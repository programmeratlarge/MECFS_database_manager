# Text based user interface for controlling interactions with ME/CFS database
# This includes setting up user IDs, reading excel files and writing their contents to the database,
# and producing reports from the database

# Author: Paul Munn, Genomics Innovation Hub, Cornell University

# Version history:
# 10/19/2020: Original version
# 12/08/2021: Modified structure to store all assay data in same document


import os
from os.path import exists
# import sys
# import datetime
from colorama import Fore
# from dateutil import parser
from mongoengine import ValidationError

import data.mongo_setup as mongo_setup
from infrastructure.switchlang import switch
import infrastructure.state as state
import services.data_service as svc
from data.assay_classes import AssayMetaData
# from data.assay_classes import Proteomic
# from data.assay_classes import Cytokine
# from data.assay_classes import Metabolomic
# from data.assay_classes import scRNAseq

import pandas as pd
import numpy as np
from random import *
from collections import defaultdict

# Set up globals
import set_up_globals
import utilities
from data.clinical_data import ClinicalData

MECFSVersion = set_up_globals.MECFSVersion
data_folder = set_up_globals.data_folder


def main():
    mongo_setup.global_init(set_up_globals.database_name)
    print_header()

    while not state.active_account:
        try:
            response = log_into_account()
            if response in set_up_globals.exitResponseList:
                exit_app()

        except KeyboardInterrupt:
            return

    show_commands()

    try:
        while True:
            action = get_action()

            with switch(action) as s:
                s.case('a', import_assay_data)
                # s.case('e', import_enid_data)
                s.case('d', import_clinical_data)
                s.case('b', import_biospecimen_data)
                s.case('scrna', import_scrnaseq_summary_data)
                s.case('dlt', import_data_label_types)
                s.case('compids', import_compound_ids)
                s.case('pathways', import_pathway_data)
                s.case('cps', calculate_pathway_summaries)
                s.case('bins', export_binned_summary)
                s.case('pseudo', export_pseudobulk_for_rti)
                s.case('seahorse', export_seahorse_for_rti)
                s.case('cpetrecovery', export_CPET_recovery_for_rti)
                s.case('evpilotstudy', export_ev_pilot_study_for_rti)
                s.case('ev_proteomics_brc', export_ev_proteomics_brc_for_rti)
                s.case('export', export_data_for_rti)
                s.case('scpaper', export_for_single_cell_paper)
                s.case('cdlt', combine_data_label_types)
                s.case('tp', test_pathway_mapping)
                s.case('vc', list_clinical_data)
                s.case('vb', list_biospecimen_data_for_study_id)
                s.case('vsc', list_biospecimen_data_for_scrnaseq_summary)
                s.case('vosc', list_only_scrnaseq_summary)
                s.case('demo', generate_demo_data)
                s.case(set_up_globals.exitResponseList, exit_app)  # ['x', 'bye', 'exit', 'exit()']
                s.case('?', show_commands)
                s.case('', lambda: None)
                s.default(unknown_command)

            if action:
                print()

    except KeyboardInterrupt:
        return


def show_commands():
    print('What action would you like to take:')
    print('[B] Import biospecimen data')
    # print(f'[E] Import {set_up_globals.enid_document_name} data')
    print(f'[D] Import {set_up_globals.clinical_document_name} data')
    print('[A] Import assay data (Proteomics, Cytokines, Metabolomics, etc.)')
    # print('[scRNA] Import scRNA-seq summary data')
    # print('[dlt] Import data label types')
    # print('[compids] Import compound IDs')
    # print('[pathways] Import pathway data')
    # print('[cps] Calculate gene pathway summaries')
    print('[Bins] Export a binned summary of demographic data')
    # print('[pseudo] Export pseudobulk data in format for import into mapMECFS')
    # print('[seahorse] Export seahorse data in format for import into mapMECFS')
    # print('[cpetrecovery] Export CPET recovery data in format for import into mapMECFS')
    # print('[evpilotstudy] Export EV pilot study data in format for import into mapMECFS')
    print('[Export] Export data in format for import into mapMECFS')
    # print('[ev_proteomics_brc] Export EV Proteomics BRC data in format for import into mapMECFS')
    # print('[scpaper] Export phenotype data for single cell manuscript')
    # print('[cdlt] Combine data label types')
    # print('[tp] Test pathway mapping across two assays')
    print(f'[vc] View {set_up_globals.clinical_document_name} data')
    print('[vb] View biospecimen data for a study ID')
    # print('[vsc] View biospecimen data for each scRNA-seq summary')
    # print('[vosc] View only scRNA-seq summary data')
    # print('[demo] Generate random demo data')
    # print('Change [M]ode (guest or host)')
    print('e[X]it app')
    print('[?] Help (this info)')
    print()


def create_account():
    print(' ******************** REGISTER ******************** ')

    name = input('What is your name? ')
    email = input('What is your email? ').strip().lower()

    old_account = svc.find_account_by_email(email)
    if old_account:
        error_msg(f"ERROR: Account with email {email} already exists.")
        return

    state.active_account = svc.create_account(name, email)
    success_msg(f"Created new account with id {state.active_account.id}.")


def log_into_account():
    print(' ******************** Select user ******************** ')

    for user_tuple in set_up_globals.users:
        name = user_tuple[0]
        email = user_tuple[1]
        if not svc.find_account_by_email(email):
            svc.create_account(name, email)

    users = svc.get_users()
    print()
    for idx, u in enumerate(users):
        print('{}. {} (email: {})'.format(
            idx + 1,
            u.name,
            u.email
        ))

    message = f"\nPlease enter a number between 1 and {str(len(users))} or 'x' to exit: "
    response = input(message)
    if response in set_up_globals.exitResponseList:
        return response

    try:
        user = users[int(response) - 1]
    except (IndexError, ValueError):
        error_msg(message + '\n')
        return response

    email = user.email
    account = svc.find_account_by_email(email)
    if not account:
        error_msg(f'Could not find account with email {email}.')
        return response

    state.active_account = account
    success_msg('Logged in successfully.')


def modify_df_column_names(column_names, classColumnList=None):
    renamed_columns = []
    for i in range(len(column_names)):
        original_col = str(column_names[i]).strip()
        col = utilities.modify_string(original_col)

        # If classColumnsList exists then restrict column names to only those in the class
        # This prevents the changing of gene symbols that are included as columns in th Excel spreadsheet
        if (classColumnList is not None) and (col not in classColumnList):
            renamed_columns.append(original_col)
        else:
            renamed_columns.append(col)

    return renamed_columns


def create_custom_columns(df, documentName, data_file_name, index_column=None):
    #  Acts like pass by reference if I add data to df, rather than
    #  assigning a new value to df, so no need to return a value
    # print('Document name:', documentName)
    df['data_file_name'] = data_file_name

    if documentName == set_up_globals.scrnaseq_summary_document_name:
        df['study_id'] = df['enid']

    if documentName == set_up_globals.proteomics_document_name or \
            documentName == set_up_globals.cytokines_document_name or \
            documentName == set_up_globals.metabolomics_document_name or \
            documentName == set_up_globals.mirnaseq_document_name or \
            documentName == set_up_globals.scrnaseq_document_name or \
            documentName == 'CPET' or \
            documentName == set_up_globals.cpet_recovery_document_name or \
            documentName == 'Other':
        df['study_id'] = df['ENID']

        validTimePoints = ['D1-PRE', 'D1-POST', 'D2-PRE', 'D2-POST', 'Other', '0h', '15min', '24h', 'D1', 'D2']
        timepoint_list = []
        for val in df['timepoint']:
            # print('Val:', val)
            if val in validTimePoints:
                timepoint_list.append(val)
            elif val.lower() == 'pre-day1':
                timepoint_list.append('D1-PRE')
            elif val.lower() == 'post-day1':
                timepoint_list.append('D1-POST')
            elif val.lower() == 'pre-day2':
                timepoint_list.append('D2-PRE')
            elif val.lower() == 'post-day2':
                timepoint_list.append('D2-POST')
            else:
                timepoint_list.append('')
        df['timepoint'] = timepoint_list

        # Set up unique_id column
        print('index column:', index_column)
        # print('row:', row)
        if index_column == 'AnalysisID':
            # df.dropna(axis=0, subset=[index_column], inplace=True)  # Remove nulls from index
            # //--- flag null value in the event log
            index_names = df[df[index_column] == ''].index
            df.drop(index_names, inplace=True)
            df['unique_id'] = df[index_column]
        elif index_column == 'ENID+Timepoint':
            # //--- flag null values in the event log
            # //--- I'm sure there's a way of doing this in one line, but this way is more readable : )
            unique_id_list = []
            for index, row in df.iterrows():
                unique_id_list.append(svc.convert_to_string(row.study_id) + '-' + row.timepoint + '-' + data_file_name)
            df['unique_id'] = unique_id_list
        elif index_column == 'ENID+Timepoint+Annot-1':
            # This assumes that Annot-1 contains a value that will make the ID unique
            # e.g. 'Cluster' in the case of scRNAseq data
            # //--- flag null values in the event log
            # //--- I'm sure there's a way of doing this in one line, but this way is more readable : )
            unique_id_list = []
            for index, row in df.iterrows():
                unique_id_list.append(svc.convert_to_string(row.study_id) + '-' + row.timepoint + '-' + str(
                    row.annot_1) + '-' + data_file_name)
            # print('unique_id_list:', unique_id_list)
            df['unique_id'] = unique_id_list
        elif index_column == 'ENID+Timepoint+Annot-1+Annot-2':
            # This assumes that Annot-1 + Annot-2 contain values that will make the ID unique
            unique_id_list = []
            for index, row in df.iterrows():
                unique_id_list.append(svc.convert_to_string(row.study_id) + '-' + row.timepoint + '-' +
                                      str(row.annot_1) + '-' + str(row.annot_2) + '-' + data_file_name)
            df['unique_id'] = unique_id_list
        # else:
        #     error_msg(f'Error: {index_column} is not a valid sample identifier type')
        #     error_msg('Exiting data load')
        #     return  # None, None

    if documentName == set_up_globals.biospecimen_document_name:
        df['sample_id'] = df['id']
        # Set Specimen ID to ENID, CPET Day, Pre/Post, and Specimen type
        # //--- this may not be needed in biospecimen spread sheet removes tube number from specimen id column
        # //--- I'm sure there's a way of doing this in one line, but this way is more readable : )
        specimen_id_list = []
        for val in df['specimen_id']:
            valMinusTubeNumberList = val.split('-')[0:4]
            specimen_id_list.append('-'.join(valMinusTubeNumberList))
        df['specimen_id'] = specimen_id_list

    if documentName == set_up_globals.clinical_document_name:
        # Make sure study ID is numeric (i.e. strip off 'ENID' if it exists)
        study_id_list = [int(val.strip('ENID')) for val in df['study_id']]
        df['study_id'] = study_id_list

        # Create columns for binned values
        for binColumn in set_up_globals.binnedColumnsDict:
            df[binColumn + '_binned'] = ''

    if documentName == set_up_globals.data_label_type_document_name:
        df['unique_id'] = df.index
        if 'comp_id' not in df.columns:
            df['comp_id'] = ''
            df['biochemical'] = ''
        if 'gene_name' not in df.columns:
            df['gene_name'] = ''
        if 'gene_stable_id' not in df.columns:
            df['gene_stable_id'] = ''
        if 'cytokine_label' not in df.columns:
            df['cytokine_label'] = ''
        # //--- set up remaining data labels - let's do this without the hardcoding

    if documentName == set_up_globals.seahorse_document_name:
        df['unique_id'] = df[index_column]

    if documentName == set_up_globals.cpet_recovery_document_name:
        df['pub_id'] = df['ENID']
        # unique_id_list = []
        # for index, row in df.iterrows():
        #     unique_id_list.append(svc.convert_to_string(row.pub_id) + '-' + svc.convert_to_string(row.timepoint) + '-' + data_file_name)
        # df['unique_id'] = unique_id_list

    if documentName == set_up_globals.ev_pilot_study_document_name:
        df['unique_id'] = df['ENID']


def import_data(documentName, index_column, verifyIntegrityFlag=True, sheet_name=0, skiprows=None):
    print(f' ******************** Import {documentName} data ******************** ')

    # Look up file
    items = os.listdir(data_folder)
    fileList = []
    for names in items:
        if (names.endswith('.xlsx') or names.endswith('.xls')) and not names.startswith('~'):
            fileList.append(names)

    for idx, fileName in enumerate(fileList):
        print('{}. {}'.format(
            idx + 1,
            fileName
        ))

    message = f"\nPlease select a file number between 1 and {str(len(fileList))}: "
    response = input(message)
    # if response in set_up_globals.exitResponseList:
    #     return None, None

    try:
        data_file_name = fileList[int(response) - 1]
    except (IndexError, ValueError):
        error_msg('\nError: You did not make a valid file selection \n')
        return None, None

    engine = 'openpyxl'  # Support for xlxs file format
    if data_file_name.split('.')[1] == 'xls':
        engine = 'xlrd'  # Support for xls file format
    df = pd.read_excel(data_folder + data_file_name,
                       sheet_name=sheet_name, skiprows=skiprows, engine=engine, keep_default_na=False)

    df.columns = modify_df_column_names(df.columns)
    index_names = df[df[index_column] == ''].index
    df.drop(index_names, inplace=True)
    # df.dropna(axis=0, subset=[index_column], inplace=True)  # Remove nulls from index

    # Create custom columns
    create_custom_columns(df, documentName, data_file_name)
    df.set_index(index_column, drop=False, inplace=True, verify_integrity=verifyIntegrityFlag)

    return df, data_file_name


def import_assay_data():
    df, data_file_name, metaDataDict, documentName, fastLoad = import_custom_assay_data()

    # # Look up file
    # items = os.listdir(data_folder)
    # fileList = []
    # for names in items:
    #     if (names.endswith('.xlsx') or names.endswith('.xls')) and not names.startswith('~'):
    #         fileList.append(names)
    #
    # for idx, fileName in enumerate(fileList):
    #     print('{}. {}'.format(
    #         idx + 1,
    #         fileName
    #     ))
    #
    # message = f"\nPlease select a file number between 1 and {str(len(fileList))}: "
    # response = input(message)
    # # //--- need some error checking here
    # # if response in set_up_globals.exitResponseList:
    # #     return  # None, None
    #
    # try:
    #     data_file_name = fileList[int(response) - 1]
    # except (IndexError, ValueError):
    #     error_msg('\nError: You did not make a valid file selection \n')
    #     return  # None, None
    #
    # # Start by reading metadata sheet
    # # Need to know: documentName, index_column, sheet_name, and skiprows before reading data sheet
    # metaDataDict = {'submitter_name': None,
    #                 'submitter_netid': None,
    #                 'pi_name': None,
    #                 'unique_assay_name': None,
    #                 'assay_type': None,
    #                 'assay_method': None,
    #                 'biospecimen_type': None,
    #                 'sample_identifier_type': None,
    #                 'dataset_name': None,
    #                 'dataset_annotation': None,
    #                 'data_label_type': None,
    #                 'comment': None,
    #                 'units': None,
    #                 'normalization_method': None,
    #                 'pipeline': None,
    #                 'title': None,
    #                 'description': None,
    #                 'tags': None,
    #                 'organization': None,
    #                 'current_visibility': None,
    #                 'data_type': None,
    #                 'organism': None,
    #                 'assay': None,
    #                 'measurement': None,
    #                 'study_type': None,
    #                 'sample': None,
    #                 'file_name_location': None,
    #                 }
    # engine = 'openpyxl'  # Support for xlxs file format
    # if data_file_name.split('.')[1] == 'xls':
    #     engine = 'xlrd'  # Support for xls file format
    # skiprows = range(0, 3)
    # metaDataDF = pd.read_excel(data_folder + data_file_name,
    #                            sheet_name='Metadata', skiprows=skiprows, engine=engine, keep_default_na=False)
    # for i, row in metaDataDF.iterrows():
    #     metaDataType = modify_df_column_names([str(row[0]).lower()])[0]
    #     response = str(row[1])
    #     if metaDataType in metaDataDict and len(response.strip()) > 0 and response.strip().lower() != 'nan':
    #         metaDataDict[metaDataType] = response.strip()
    #
    # # Display what was just read
    # print('')
    # for key, val in metaDataDict.items():
    #     print(key, ':', val)
    #
    # # Check assay type
    # # //--- replace all these with global references
    # validAssayTypes = [set_up_globals.proteomics_document_name,
    #                    set_up_globals.cytokines_document_name,
    #                    set_up_globals.metabolomics_document_name,
    #                    set_up_globals.mirnaseq_document_name,
    #                    set_up_globals.scrnaseq_document_name,
    #                    'BDNF',
    #                    'CPET',
    #                    'LPS',
    #                    'Other']
    # documentName = metaDataDict['assay_type']
    # if documentName not in validAssayTypes:
    #     error_msg(f'Error: {documentName} is not a valid assay type')
    #     error_msg('Exiting data load')
    #     return  # None, None
    #
    # # If separate file specified, check that it exists
    # externalFileName = ''
    # if metaDataDict['file_name_location'] is not None:
    #     externalFileName = data_folder + metaDataDict['file_name_location']
    #     if not exists(externalFileName):
    #         error_msg(f'Error: {externalFileName} does not exist')
    #         error_msg('Exiting data load')
    #         return  # None, None
    #
    # message = f"\nIs this correct? (y/n): "
    # response = input(message)
    # if response[0].lower() != 'y':
    #     return  # None, None
    #
    # print(f' ******************** Import {documentName} data ******************** ')
    #
    # # If link to file exists, read data from there, otherwise read data from 'Data Table' tab of spreadsheet
    # if len(externalFileName) == 0:  # Read data from 'Data Table' tab
    #     skiprows = range(0, 1)  # //--- for now, define skiprows as the top row - can adjust this later
    #     df = pd.read_excel(data_folder + data_file_name,
    #                        sheet_name='Data Table', skiprows=skiprows, engine=engine, keep_default_na=False)
    # else:  # Read data from external file
    #     df = pd.read_csv(externalFileName, sep='\t', header=0, keep_default_na=False)
    #
    # # Remove nulls from ENID
    # index_names = df[df['ENID'] == ''].index
    # df.drop(index_names, inplace=True)
    #
    # # Remove unnamed columns
    # unnamedColList = [colName for colName in df.columns if str(colName).startswith('Unnamed')]
    # df.drop(labels=unnamedColList, axis='columns', inplace=True)
    #
    # # Get column names
    # classColumnList = utilities.attributes(AssayMetaData)
    # df.columns = modify_df_column_names(df.columns, classColumnList)
    #
    # # Create custom columns
    # create_custom_columns(df, documentName, data_file_name, metaDataDict['sample_identifier_type'])
    #
    # try:
    #     df.set_index('unique_id', drop=False, inplace=True, verify_integrity=True)
    # except (ValueError, ValidationError) as e:
    #     message = f'Create of index for {documentName} data resulted in exception: {e}'
    #     error_msg(message)
    #     error_msg('No data saved')
    #     return  # Skip the rest of this function
    #
    # # Fast load: assumes that all assay data in new and aso skips the reference to the biospecimen
    # fastLoad = False
    # if documentName == set_up_globals.scrnaseq_document_name: fastLoad = True

    # Save assay meta data
    svc.add_assay_meta_data(state.active_account, df, data_file_name, metaDataDict, documentName, fastLoad=fastLoad)

    return


def import_data_label_types():
    documentName = set_up_globals.data_label_type_document_name
    df, data_file_name = import_data(documentName, 'gene_name', verifyIntegrityFlag=False)
    svc.add_data_label_types(state.active_account, df, data_file_name)


def combine_data_label_types():
    documentName = set_up_globals.data_label_type_document_name

    # Read two spreadsheets to combine
    df, data_file_name = import_data(documentName, 'gene_name', verifyIntegrityFlag=False)
    cytokine_df, data_file_name = import_data(documentName, 'entrezgenessymbol', verifyIntegrityFlag=False)
    print(df.head(5))
    print(cytokine_df.head(5))

    # Add cytokine column to main df
    geneToCytokineTranslationDict = {}
    for index, row in cytokine_df.iterrows():
        geneToCytokineTranslationDict[row['entrezgenessymbol']] = row['cytokine']
    # print('geneToCytokineTranslationDict', geneToCytokineTranslationDict)
    df['cytokine_label'] = ''
    # print(df.head(5))
    for index, row in df.iterrows():
        if row['gene_name'] in geneToCytokineTranslationDict:
            df.loc[index, 'cytokine_label'] = geneToCytokineTranslationDict[row['gene_name']]
    print(df.head(5))

    # Write combined df to new spreadsheet
    output_data_file_name = 'combined_gene_names_and_cytokines.xlsx'
    df.to_excel(data_folder + output_data_file_name)


def import_compound_ids():
    documentName = set_up_globals.data_label_type_document_name
    df, data_file_name = import_data(documentName, 'comp_id', verifyIntegrityFlag=False)
    svc.add_data_label_types(state.active_account, df, data_file_name)


def import_pathway_data():
    documentName = set_up_globals.data_label_pathway_document_name
    df, data_file_name = import_data(documentName, 'pathway_name', verifyIntegrityFlag=False)
    svc.add_data_label_pathways(state.active_account, df, data_file_name)


def import_enid_data():
    documentName = set_up_globals.enid_document_name
    df, data_file_name = import_data(documentName, 'enid_number')
    svc.add_enid_data(state.active_account, df, data_file_name)


def import_clinical_data():
    documentName = set_up_globals.clinical_document_name
    df, data_file_name = import_data(documentName, 'study_id')
    svc.add_clinical_data(state.active_account, df, data_file_name)


def import_biospecimen_data():
    documentName = set_up_globals.biospecimen_document_name
    df, data_file_name = import_data(documentName, 'specimen_id', verifyIntegrityFlag=False)
    svc.add_biospecimen_data(state.active_account, df, data_file_name)


def import_scrnaseq_summary_data():
    documentName = set_up_globals.scrnaseq_summary_document_name
    df, data_file_name = import_data(documentName, 'sampleid', sheet_name=0, skiprows=range(0, 3))
    svc.add_scrnaseq_summary_data(state.active_account, df, data_file_name)


# Export demographic info for mapMECFS with data from certain fields reported as bins
def export_binned_summary():
    print(' ********************     Export binned demographic summary     ******************** ')

    useSingleCellENIDsOnly = False

    # Sex, age, BMI, SF36 domains (GH, PCS), MFI, whether onset was sudden or gradual, Bell score
    # columns = set_up_globals.exportDemographicColumnsForSCpaper
    columns = set_up_globals.exportDemographicColumnsForRTIFull

    # columns = ['study_id', 'cor_id', 'site', 'sex', 'phenotype',
    #            'age', 'age_binned', 'bmi', 'bmi_binned', 'mecfs_sudden_gradual',
    #            'PF', 'RP', 'BP', 'GH', 'VT', 'SF', 'RE', 'MH', 'PF_NBS', 'RP_NBS', 'BP_NBS',
    #            'GH_NBS', 'VT_NBS', 'SF_NBS', 'RE_NBS', 'MH_NBS', 'PCS', 'MCS', 'bas_score',
    #            'mfi20_gf', 'mfi20_pf', 'mfi20_ra', 'mfi20_rm', 'mfi20_mf', 'mfi20_total',
    #            'q_oisymptoms', 'q_gisymptoms', 'q_probiotics', 'q_sleeprefreshing']

    binnedColumns = ['age', 'bmi', 'PF', 'RP', 'BP', 'GH', 'VT', 'SF', 'RE', 'MH', 'PCS', 'MCS', 'PF_NBS', 'RP_NBS', 'BP_NBS', 'GH_NBS', 'VT_NBS', 'SF_NBS', 'RE_NBS', 'MH_NBS', 'mfi20_gf', 'mfi20_pf', 'mfi20_ra', 'mfi20_rm', 'mfi20_mf', 'mfi20_total', 'bas_score']
    customBinnedColumns = ['age', 'bmi', 'PF', 'RP', 'BP', 'GH', 'VT', 'SF', 'RE', 'MH', 'PCS', 'MCS', 'PF_NBS', 'RP_NBS', 'BP_NBS', 'GH_NBS', 'VT_NBS', 'SF_NBS', 'RE_NBS', 'MH_NBS', 'mfi20_gf', 'mfi20_pf', 'mfi20_ra', 'mfi20_rm', 'mfi20_mf', 'mfi20_total', 'bas_score']
    # binnedColumns = ['age', 'bmi', 'PF', 'RP', 'BP', 'GH', 'VT', 'SF', 'RE', 'MH', 'PCS', 'MCS', 'mfi20_total', 'bas_score']
    # customBinnedColumns = ['age', 'bmi', 'PF', 'RP', 'BP', 'GH', 'VT', 'SF', 'RE', 'MH', 'PCS', 'MCS', 'mfi20_total', 'bas_score']
    # binnedColumns = ['age', 'bmi', 'mecfs_duration', 'GH', 'PCS', 'mfi20_total', 'pem_max_delta']
    # customBinnedColumns = ['age', 'bmi', 'mecfs_duration', 'GH', 'PCS', 'mfi20_total', 'pem_max_delta']
    # binnedColumns = ['age', 'bmi']
    # customBinnedColumns = ['age', 'bmi']

    desiredNumberOfBins = 5
    minNumberOfPeoplePerBin = 3
    fixedBinSize = False

    modifiedColumns = modify_df_column_names(columns)
    modifiedBinnedColumns = modify_df_column_names(binnedColumns)
    modifiedCustomBinnedColumns = modify_df_column_names(customBinnedColumns)

    # Set bin size for each type of bin / set up counts for each type of bin
    binCountsDict = defaultdict(dict)
    binSizeDict = {}
    binMinDict = {}
    for i in range(0, len(modifiedBinnedColumns)):
        binSizeDict[modifiedBinnedColumns[i]] = 0
        # binSizeDict[modifiedBinnedColumns[i]] = binnedColumnsSize[i]
        binCountsDict[modifiedBinnedColumns[i]] = defaultdict(int)
        binMinDict[modifiedBinnedColumns[i]] = 0
        if modifiedBinnedColumns[i] in modifiedCustomBinnedColumns:
            binRangeTuples = set_up_globals.binnedColumnsDict[modifiedBinnedColumns[i]]
            binNumber = 1
            for binRange in binRangeTuples:
                binStart = float(binRange[0])
                binEnd = float(binRange[1])
                binCountsDict[modifiedBinnedColumns[i]][binNumber] = [0, binStart, binEnd, 0, 0, 0, 0, 0, 0]
                binNumber += 1
            # if modifiedBinnedColumns[i] == 'age':
            #     binCountsDict[modifiedBinnedColumns[i]][1] = [0, 0, 35, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][2] = [0, 35, 45, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][3] = [0, 45, 55, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][4] = [0, 55, 100, 0, 0, 0, 0, 0, 0]
            # if modifiedBinnedColumns[i] == 'bmi':
            #     binCountsDict[modifiedBinnedColumns[i]][1] = [0, 0.0, 25.0, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][2] = [0, 25.0, 27.0, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][3] = [0, 27.0, 30.0, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][4] = [0, 30.0, 100.0, 0, 0, 0, 0, 0, 0]
            # if modifiedBinnedColumns[i] == 'bmi':
            #     binCountsDict[modifiedBinnedColumns[i]][1] = [0, 0, 18.5, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][2] = [0, 18.5, 25, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][3] = [0, 25, 30, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][4] = [0, 30, 35, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][5] = [0, 35, 100, 0, 0, 0, 0, 0, 0]
            # if modifiedBinnedColumns[i] == 'mecfs_duration':
            #     binCountsDict[modifiedBinnedColumns[i]][1] = [0, 0, 5, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][2] = [0, 5, 10, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][3] = [0, 10, 15, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][4] = [0, 15, 20, 0, 0, 0, 0, 0, 0]
            #     binCountsDict[modifiedBinnedColumns[i]][5] = [0, 20, 100, 0, 0, 0, 0, 0, 0]

    # Get a list of all the subjects in the database
    # documentName = set_up_globals.clinical_document_name
    # df, data_file_name = import_data(documentName, 'study_id')
    clinicalDataObjectList = svc.find_clinical_data()

    # Get list of unique assay names
    uniqueAssayList = svc.find_unique_assay_names()
    # first_unique_assay_name = uniqueAssayList[0]

    df, dataGeneSymbolList = utilities.create_df_from_object_list(clinicalDataObjectList,
                                                                  [AssayMetaData],
                                                                  ['assay_meta_data'],
                                                                  uniqueAssayList,
                                                                  assayResultsFlag=True,
                                                                  assaySummaryFlag=False)

    # Set up lists of patients and controls with single-cell and metabolomics data
    patientENIDs = [101, 171, 483, 287, 416, 408, 588, 115, 199, 329, 191, 128, 344, 135, 196, 112, 380, 160, 440, 316,
                    463, 447, 235, 299, 369, 473, 405, 554, 500, 730]
    controlENIDs = [181, 241, 467, 375, 656, 723, 637, 715, 711, 145, 164, 197, 119, 143, 359, 261, 297, 406, 276, 210,
                    338, 333, 481, 724, 791, 788, 727, 760]
    metabolomicsPatientENIDs = [101, 112, 115, 128, 135, 136, 160, 171, 191, 196, 199, 204, 205, 223, 228, 230, 235,
                                240, 264, 284, 287, 290, 299, 311, 316, 350, 358, 369, 372, 380, 396, 403, 405, 408,
                                416, 420, 440, 447, 463, 473, 483, 500, 521, 523, 524, 526, 551, 554, 558, 576, 583,
                                588, 594, 600, 678, 679, 698, 701, 702, 730]
    metabolomicsControlENIDs = [119, 143, 145, 164, 181, 197, 210, 241, 261, 276, 297, 333, 338, 347, 375, 406, 410,
                                413, 467, 481, 488, 506, 563, 606, 607, 622, 637, 656, 685, 711, 712, 715, 722, 723,
                                724, 727, 732, 759, 760, 771, 774, 784, 788, 791, 811]
    populationToConsider = patientENIDs
    if useSingleCellENIDsOnly: desiredNumberOfBins = desiredNumberOfBins - 1

    # Set up dataframe to export
    df = df[df.phenotype.notnull()]
    df = df[df.phenotype.isin(['HC', 'ME/CFS'])]
    if useSingleCellENIDsOnly: df = df[df.study_id.isin(patientENIDs + controlENIDs)]

    # Build custom summary columns
    df['pem_change_d1_to_d2'] = df['sss_cpet2_pre_9'] - df['sss_cpet1_pre_9']
    df['pem_change_2days_post'] = df['sss_2days_post_9'] - df['sss_cpet1_pre_9']
    df['pem_change_4days_post'] = df['sss_4days_post_9'] - df['sss_cpet1_pre_9']
    df['pem_change_6days_post'] = df['sss_6days_post_9'] - df['sss_cpet1_pre_9']
    df['pem_change_8days_post'] = df['sss_8days_post_9'] - df['sss_cpet1_pre_9']
    df['pem_change_10days_post'] = df['sss_10days_post_9'] - df['sss_cpet1_pre_9']
    df['pem_max_delta'] = ''
    for index, row in df.iterrows():
        if str(df.loc[index, 'pem_change_d1_to_d2']) == 'nan': df.loc[index, 'pem_change_d1_to_d2'] = 0
        if str(df.loc[index, 'pem_change_2days_post']) == 'nan': df.loc[index, 'pem_change_2days_post'] = 0
        if str(df.loc[index, 'pem_change_4days_post']) == 'nan': df.loc[index, 'pem_change_4days_post'] = 0
        if str(df.loc[index, 'pem_change_6days_post']) == 'nan': df.loc[index, 'pem_change_6days_post'] = 0
        if str(df.loc[index, 'pem_change_8days_post']) == 'nan': df.loc[index, 'pem_change_8days_post'] = 0
        if str(df.loc[index, 'pem_change_10days_post']) == 'nan': df.loc[index, 'pem_change_10days_post'] = 0
        df.loc[index, 'pem_max_delta'] = abs(max(df.loc[index, 'pem_change_d1_to_d2'],
                                            df.loc[index, 'pem_change_2days_post'],
                                            df.loc[index, 'pem_change_4days_post'],
                                            df.loc[index, 'pem_change_6days_post'],
                                            df.loc[index, 'pem_change_8days_post'],
                                            df.loc[index, 'pem_change_10days_post'], key=abs))
        # if df.loc[index, 'cor_id'] == 'COR-1481':
        #     print('pem_change_d1_to_d2: ' + str(df.loc[index, 'pem_change_d1_to_d2']))
        #     print('pem_change_2days_post: ' + str(df.loc[index, 'pem_change_2days_post']))
        #     print('pem_change_4days_post: ' + str(df.loc[index, 'pem_change_4days_post']))
        #     print('pem_change_6days_post: ' + str(df.loc[index, 'pem_change_6days_post']))
        #     print('pem_change_8days_post: ' + str(df.loc[index, 'pem_change_8days_post']))
        #     print('pem_change_10days_post: ' + str(df.loc[index, 'pem_change_10days_post']))
        #     print('pem_max_delta: ' + str(df.loc[index, 'pem_max_delta']))
        #     sys.exit(2)
    # print('df:', df.head(10))

    exportSummaryDF = pd.DataFrame(columns=modifiedColumns)
    for col in exportSummaryDF.columns:
        exportSummaryDF[col] = df[col]
        if col == 'pcs': exportSummaryDF[col] = exportSummaryDF[col].round(0)
        if col in modifiedBinnedColumns:
            binMinDict[col] = df[col].min()

    exportSummaryDF = exportSummaryDF.drop_duplicates()
    print(f"There are {len(exportSummaryDF)} records.")
    # print(df.head(5))
    # print(df.columns)
    # print(sorted(binCountsDict))

    # for idx, row in exportSummaryDF.sort_values('weight_lbs').iterrows():
    #     print(' {}. {}: {}'.format(idx + 1, row.study_id, row.weight_lbs))

    if fixedBinSize:
        for binName in modifiedBinnedColumns:
            if binName in modifiedCustomBinnedColumns: continue
            for binSize in range(1, 100):
                binSizeDict[binName] = binSize
                countDict = defaultdict(int)
                for idx, row in exportSummaryDF.iterrows():
                    if not utilities.isNumber(row[binName]): continue
                    if useSingleCellENIDsOnly and row['study_id'] not in populationToConsider: continue
                    offsetBinValue = row[binName] - binMinDict[binName]
                    binNumber = int(int(offsetBinValue) / binSize) + 1
                    if binNumber not in countDict:
                        countDict[binNumber] = 1
                    else:
                        countDict[binNumber] += 1
                keepGoing = False
                for binNumber in countDict:
                    if countDict[binNumber] < minNumberOfPeoplePerBin:
                        keepGoing = True
                if not keepGoing: break
            for binNumber in countDict:
                binCountsDict[binName][binNumber] = [0, (binNumber - 1) * binSize + binMinDict[binName],
                                                     binNumber * binSize - 1 + binMinDict[binName], 0, 0, 0, 0, 0, 0]
        # print(binSizeDict)
    else:
        for binName in modifiedBinnedColumns:
            if binName in modifiedCustomBinnedColumns: continue
            countDict = defaultdict(int)
            binNumber = 1
            if useSingleCellENIDsOnly:
                numberOfPeoplePerBin = int(len(populationToConsider) / desiredNumberOfBins) - 1
            else:
                nonZeroCount = exportSummaryDF[binName].fillna(0).astype(bool).sum(axis=0)
                numberOfPeoplePerBin = int(nonZeroCount / desiredNumberOfBins)

            for idx, row in exportSummaryDF.sort_values(binName).iterrows():
                if not utilities.isNumber(row[binName]): continue
                # if useSingleCellENIDsOnly and row['study_id'] not in populationToConsider: continue

                if binNumber not in sorted(binCountsDict[binName]):
                    binCountsDict[binName][binNumber] = [0, float(row[binName]), float(row[binName]), 0, 0, 0, 0, 0, 0]
                    countDict[binNumber] = 0
                    if useSingleCellENIDsOnly:
                        if row['study_id'] in populationToConsider: countDict[binNumber] += 1
                    else:
                        countDict[binNumber] += 1
                else:
                    if useSingleCellENIDsOnly:
                        if row['study_id'] in populationToConsider: countDict[binNumber] += 1
                    else:
                        countDict[binNumber] += 1
                    binCountsDict[binName][binNumber][2] = float(row[binName])
                if countDict[binNumber] >= numberOfPeoplePerBin:
                    binNumber += 1
                    binCountsDict[binName][binNumber] = [0, float(row[binName]), float(row[binName]), 0, 0, 0, 0, 0, 0]
                    countDict[binNumber] = 0

    # Reset lower and upper limits on first and last bins
    # Hardcode first two bins of duration
    for binName in binCountsDict:
        if binName in modifiedCustomBinnedColumns: continue
        for binNumber in sorted(binCountsDict[binName]):
            if binNumber == 1:
                binCountsDict[binName][binNumber][1] = 0  # Set lower limit of first bin to zero
                if binName == 'mecfs_duration': binCountsDict[binName][binNumber][2] = 5
            if binNumber == 2 and binName == 'mecfs_duration': binCountsDict[binName][binNumber][1] = 5
            if binNumber == max(binCountsDict[binName], key=int): binCountsDict[binName][binNumber][
                2] = 100  # Set upper limit of last bin to 100

    print('Before calculate bins')
    for binNumber in sorted(binCountsDict['bmi']):
        print('binCountsDict:', str(binNumber), binCountsDict['bmi'][binNumber])

    # Calculate bins
    for binName in binCountsDict:
        exportSummaryDF[binName + '_binned'] = ''

    for idx, row in exportSummaryDF.iterrows():
        # print(' {}. {}: {}'.format(idx + 1, row.study_id, row.age))

        for binName in binCountsDict:
            if not utilities.isNumber(row[binName]): continue
            for binNumber in sorted(binCountsDict[binName]):
                binList = binCountsDict[binName][binNumber]
                binStart = float(binList[1])
                binEnd = float(binList[2])
                if (binNumber == 1 and float(row[binName]) >= binStart and float(row[binName]) <= binEnd) or \
                        (float(row[binName]) > binStart and float(row[binName]) <= binEnd):
                    exportSummaryDF.loc[idx, binName + '_binned'] = binNumber
                    binCountsDict[binName][binNumber][0] += 1
                    # Update case and control counts
                    if row['phenotype'] == 'ME/CFS':
                        binCountsDict[binName][binNumber][3] += 1
                        if row['study_id'] in patientENIDs: binCountsDict[binName][binNumber][5] += 1
                        if row['study_id'] in metabolomicsPatientENIDs: binCountsDict[binName][binNumber][7] += 1
                    else:
                        binCountsDict[binName][binNumber][4] += 1
                        if row['study_id'] in controlENIDs: binCountsDict[binName][binNumber][6] += 1
                        if row['study_id'] in metabolomicsControlENIDs: binCountsDict[binName][binNumber][8] += 1
                    break

    # Export
    print('df:', df[['study_id', 'cor_id', 'sex', 'phenotype', 'age']].head(10))
    print('exportSummaryDF:', exportSummaryDF[['study_id', 'cor_id', 'sex', 'phenotype', 'age']].head(10))
    print('exportSummaryDF.columns:', exportSummaryDF.columns)
    print('binSizeDict:', binSizeDict)
    print('binCountsDict:', sorted(binCountsDict))

    print('\nBin summary:')
    for binName in sorted(binCountsDict):
        binSize = binSizeDict[binName]
        if fixedBinSize:
            print('\n%s bin, size: %d' % (binName, binSize))
        else:
            print('\n%s bin' % binName)
        for binNumber in sorted(binCountsDict[binName]):
            binList = binCountsDict[binName][binNumber]
            binCount = binList[0]
            binStart = binList[1]
            binEnd = binList[2]
            binCountCase = binList[3]
            binCountControl = binList[4]
            binCountCaseSC = binList[5]
            binCountControlSC = binList[6]
            binCountCaseMetabolomics = binList[7]
            binCountControlMetabolomics = binList[8]
            # binStart = (binNumber - 1) * binSize + binMinDict[bin]
            # binEnd = binNumber * binSize - 1 + binMinDict[bin]
            print(
                '     Count for %s bin %d (>%3.3f to <=%4.3f): Total: %d (Case all: %d, Control all: %d, Case single-cell: %d, Control single-cell: %d, Case metabolomics: %d, Control metabolomics: %d)' %
                (binName, binNumber, binStart, binEnd, binCount, binCountCase, binCountControl, binCountCaseSC,
                 binCountControlSC, binCountCaseMetabolomics, binCountControlMetabolomics))

    exportSummaryDF.set_index('cor_id', inplace=True)
    for binName in modifiedBinnedColumns:
        exportSummaryDF.drop(binName, axis=1, inplace=True)
    exportSummaryDF.to_excel("binned_demographics_with_study_id_2023-11-10.xlsx")
    exportSummaryDF.drop('study_id', axis=1, inplace=True)
    exportSummaryDF.to_excel("binned_demographics_2023-11-10.xlsx")

    # # Save data for export to RTI
    # # Drop all but minimum cols, add CPET day pre and post to COR id
    # minimumColumns = set_up_globals.exportDemographicColumnsForRTIMinimum
    # existingColumns = exportSummaryDF.columns
    # for col in existingColumns:
    #     if col not in minimumColumns: exportSummaryDF.drop(col, axis=1, inplace=True)
    #
    # exportSummaryForRTIDF = pd.DataFrame(columns=['ParticipantID'] + minimumColumns)
    # for idx, row in exportSummaryDF.iterrows():
    #     for cpetDay in ['-D1-PRE', '-D1-POST', '-D2-PRE', '-D2-POST']:
    #         participantID = idx + cpetDay
    #         print('row:', list(row))
    #         exportSummaryForRTIDF.loc[len(exportSummaryForRTIDF.index)] = [participantID, idx] + list(row)
    # exportSummaryForRTIDF.set_index('ParticipantID', inplace=True)
    # exportSummaryForRTIDF.rename(columns={'phenotype': 'Phenotype'}, inplace=True)
    # exportSummaryForRTIDF['Sample_Source'] = 'Plasma'  # Hardcoded sample source for metabolomics data
    #
    # exportSummaryForRTIDF.to_csv("binned_demographics_for_RTI_2023-11-10.tsv", sep="\t")


def export_pseudobulk_for_rti():
    documentName = set_up_globals.scrnaseq_document_name
    print(f' ***************     Export {documentName} pseudo bulk data for import into mapMECFS     *************** ')

    # Open transposed pseudo bulk data file
    pseudobulkDF = pd.read_csv(data_folder + 'pseudobulk_for_upload_to_MEDI.tsv', sep='\t', header=0,
                               keep_default_na=False)

    # Set up summary phenotype dataframe
    columns = ['phenotype', 'biospecimen_type'] + set_up_globals.exportAssayColumnsForRTI
    modifiedColumns = modify_df_column_names(columns)
    df = pd.DataFrame(columns=modifiedColumns)

    for study_id in pseudobulkDF.ENID.unique():
        clinical_data_list = svc.find_clinical_data_by_study_id(int(study_id))
        df.loc[len(df.index)] = [clinical_data_list.phenotype,
                                 'PBMC',
                                 clinical_data_list.cor_id,
                                 'D1-PRE',
                                 'ENID+Timepoint',
                                 '', '', '']
        df.loc[len(df.index)] = [clinical_data_list.phenotype,
                                 'PBMC',
                                 clinical_data_list.cor_id,
                                 'D2-PRE',
                                 'ENID+Timepoint',
                                 '', '', '']

    rti_phenotype_DF, outputPhenotypeFileName = svc.set_up_phenotype_export_for_rti(df, documentName.replace(' ',
                                                                                                             '_') + '_pseudobulk')

    print(f"There are {len(rti_phenotype_DF)} summary rows.")
    print(rti_phenotype_DF.head(5))
    print(rti_phenotype_DF.columns)

    # Save summary file
    rti_phenotype_DF.to_csv(data_folder + 'supplementary_data/' + outputPhenotypeFileName, sep="\t")

    # Set up assay data dataframe
    dataLabelList = list(pseudobulkDF.columns[6:])
    pseudobulkDF['cor_id'] = ''
    pseudobulkDF['sample_identifier_type'] = 'ENID+Timepoint'
    pseudobulkDF.rename(columns={'Timepoint': 'timepoint'}, inplace=True)
    pseudobulkDF.rename(columns={'Annot-1': 'annot_1'}, inplace=True)
    pseudobulkDF.rename(columns={'Annot-2': 'annot_2'}, inplace=True)
    pseudobulkDF.rename(columns={'Annot-3': 'annot_3'}, inplace=True)

    for index, row in pseudobulkDF.iterrows():
        study_id = row['ENID']
        clinical_data_list = svc.find_clinical_data_by_study_id(int(study_id))
        pseudobulkDF.loc[index, 'cor_id'] = clinical_data_list.cor_id
        if row['timepoint'] == 'Pre-Day1':
            pseudobulkDF.loc[index, 'timepoint'] = 'D1-PRE'
        else:
            pseudobulkDF.loc[index, 'timepoint'] = 'D2-PRE'

    pseudobulkDF.drop('AnalysisID', axis=1, inplace=True)
    pseudobulkDF.drop('ENID', axis=1, inplace=True)

    print('pseudobulkDF:', pseudobulkDF.head(5))
    for cluster in pseudobulkDF['annot_1'].unique():
        df = pseudobulkDF[pseudobulkDF["annot_1"] == cluster].copy()
        rtiDF_transposed, outputAssayDataFileName = svc.set_up_data_export_for_rti(df,
                                                                                   'cluster_' + str(
                                                                                       cluster) + '_' + documentName + '_pseudobulk',
                                                                                   dataLabelList)

        print(f"Saving {outputAssayDataFileName} file.")
        rtiDF_transposed.to_csv(data_folder + 'supplementary_data/' + outputAssayDataFileName, sep="\t", header=False)


def export_for_single_cell_paper():
    print(f' ***************     Export phenotype data for single cell manuscript     *************** ')

    documentName = set_up_globals.scrnaseq_document_name
    phenotype_DF, outputPhenotypeFileName = svc.set_up_phenotype_export_for_rti(df,
        documentName.replace(' ', '_') + '_' + sheet_name.lower().replace(' ', '_'))
    # phenotype_DF['cor_id'] = ''

    print(f"There are {len(phenotype_DF)} summary rows.")
    print(phenotype_DF.head(5))
    print(phenotype_DF.columns)

    # Save phenotype file
    phenotype_DF.to_csv(data_folder + 'supplementary_data/' + outputPhenotypeFileName, sep="\t")


def export_seahorse_for_rti():
    print(f' ***************     Export seahorse data for import into mapMECFS     *************** ')

    sheet_names = ['Flow Mean Intensity', 'Flow Median Intensity', 'Flux Measurements']
    for sheet_name in sheet_names:
        totalFAODF, data_file_name, metaDataDict, documentName, fastLoad = \
            import_custom_assay_data(custom_sheet_name=sheet_name, personIdentifierColumn='Identifiers')
        totalFAODF.drop('unique_id', axis=1, inplace=True)
        totalFAODF.drop('data_file_name', axis=1, inplace=True)

        print('metaDataDict:', metaDataDict)
        print('totalFAODF:', totalFAODF.head())

        # Set up summary phenotype dataframe
        columns = ['phenotype', 'biospecimen_type'] + set_up_globals.exportAssayColumnsForRTI
        modifiedColumns = modify_df_column_names(columns)
        df = pd.DataFrame(columns=modifiedColumns)

        for person_id in totalFAODF.Identifiers.unique():
            # clinical_data_list = svc.find_clinical_data_by_study_id(int(study_id))
            df.loc[len(df.index)] = [totalFAODF.loc[person_id, 'Phenotype'],
                                     metaDataDict['biospecimen_type'],
                                     person_id, '', metaDataDict['sample_identifier_type'], '', '', '']

        rti_phenotype_DF, outputPhenotypeFileName = svc.set_up_phenotype_export_for_rti(df,
                                                                                        documentName.replace(' ',
                                                                                                             '_') + '_' + sheet_name.lower().replace(
                                                                                            ' ', '_'))
        rti_phenotype_DF['cor_id'] = ''

        print(f"There are {len(rti_phenotype_DF)} summary rows.")
        print(rti_phenotype_DF.head(5))
        print(rti_phenotype_DF.columns)

        # Save summary file
        rti_phenotype_DF.to_csv(data_folder + 'supplementary_data/' + outputPhenotypeFileName, sep="\t")

        # Set up assay data dataframe
        dataLabelList = list(totalFAODF.columns[5:])
        totalFAODF['cor_id'] = totalFAODF[metaDataDict['sample_identifier_type']]
        totalFAODF['sample_identifier_type'] = metaDataDict['sample_identifier_type']
        totalFAODF['timepoint'] = ''
        totalFAODF['annot_1'] = ''
        totalFAODF['annot_2'] = ''
        totalFAODF['annot_3'] = ''

        print('dataLabelList:', dataLabelList)
        print('totalFAODF:', totalFAODF.head(5))

        rtiDF_transposed, outputAssayDataFileName = svc.set_up_data_export_for_rti(totalFAODF,
                                                                                   documentName + '_' + sheet_name.lower().replace(
                                                                                       ' ', '_'), dataLabelList)

        print(f"Saving {outputAssayDataFileName} file.")
        print('rtiDF_transposed:', rtiDF_transposed.head(5))
        rtiDF_transposed.to_csv(data_folder + 'supplementary_data/' + outputAssayDataFileName, sep="\t", header=False)


def export_CPET_recovery_for_rti():
    print(f' ***************     Export CPET recovery data for import into mapMECFS     *************** ')

    dataTableDF, data_file_name, metaDataDict, documentName, fastLoad = \
        import_custom_assay_data()
    dataTableDF.drop('unique_id', axis=1, inplace=True)
    dataTableDF.drop('data_file_name', axis=1, inplace=True)
    dataTableDF['timepoint'] = dataTableDF['timepoint'].astype(str)

    print('metaDataDict:', metaDataDict)
    print('dataTableDF:', dataTableDF.head())
    print('dataTableDF.columns:', dataTableDF.columns)

    # Set up summary phenotype dataframe
    columns = ['phenotype', 'biospecimen_type'] + set_up_globals.exportAssayColumnsForRTI
    modifiedColumns = modify_df_column_names(columns)
    df = pd.DataFrame(columns=modifiedColumns)

    for index, row in dataTableDF.iterrows():
        pub_id = row['pub_id']
        clinical_data_list = svc.find_clinical_data_by_pub_id(pub_id)
        # print('clinical_data_list:', clinical_data_list.phenotype)
        df.loc[len(df.index)] = [clinical_data_list.phenotype,
                                metaDataDict['biospecimen_type'],
                                pub_id, row['timepoint'], metaDataDict['sample_identifier_type'], row['annot_1'], '', '']

    rti_phenotype_DF, outputPhenotypeFileName = svc.set_up_phenotype_export_for_rti(df, documentName.replace(' ', '_'))
    rti_phenotype_DF.rename(columns={'cor_id': 'pub_id'}, inplace=True)

    def expand_sex(x):
        if x == 'F': return 'Female'
        elif x == 'M': return 'Male'
        else: return x

    def expand_site(x):
        if str(x) == '1': return 'ITH'
        elif str(x) == '2': return 'LA'
        elif str(x) == '3': return 'NYC'
        else: return x

    # Add custom columns for CPET recovery (sex, age, MECFS duration, and site)
    rti_phenotype_DF['sex'] = ''
    rti_phenotype_DF['age'] = ''
    rti_phenotype_DF['mecfs_duration'] = ''
    rti_phenotype_DF['site'] = ''
    for index, row in rti_phenotype_DF.iterrows():
        pub_id = row['pub_id']
        clinical_data_list = svc.find_clinical_data_by_pub_id(pub_id)
        rti_phenotype_DF.at[index, 'sex'] = expand_sex(clinical_data_list.sex)
        rti_phenotype_DF.at[index, 'age'] = clinical_data_list.age
        rti_phenotype_DF.at[index, 'mecfs_duration'] = clinical_data_list.mecfs_duration
        rti_phenotype_DF.at[index, 'site'] = expand_site(clinical_data_list.site)

        # Additions for Betsy Keller's data
        rti_phenotype_DF.at[index, 'race'] = clinical_data_list.race
        rti_phenotype_DF.at[index, 'age_binned'] = clinical_data_list.age_binned
        rti_phenotype_DF.at[index, 'height_in'] = clinical_data_list.height_in
        rti_phenotype_DF.at[index, 'weight_lbs'] = clinical_data_list.weight_lbs
        rti_phenotype_DF.at[index, 'bmi'] = clinical_data_list.bmi
        rti_phenotype_DF.at[index, 'bmi_binned'] = clinical_data_list.bmi_binned
        rti_phenotype_DF.at[index, 'bas_score'] = clinical_data_list.bas_score
        rti_phenotype_DF.at[index, 'q_education'] = clinical_data_list.q_education
        rti_phenotype_DF.at[index, 'q_reclined'] = clinical_data_list.q_reclined
        rti_phenotype_DF.at[index, 'q_sleeprefreshing'] = clinical_data_list.q_sleeprefreshing
        rti_phenotype_DF.at[index, 'q_hoursinbed'] = clinical_data_list.q_hoursinbed

    print(f"There are {len(rti_phenotype_DF)} summary rows.")
    print(rti_phenotype_DF.head(5))
    print(rti_phenotype_DF.columns)

    # Save summary file
    rti_phenotype_DF.to_csv(data_folder + 'supplementary_data/' + outputPhenotypeFileName, sep="\t")

    # Set up assay data dataframe
    dataLabelList = list(dataTableDF.columns[5:])
    dataTableDF['cor_id'] = dataTableDF['pub_id']
    dataTableDF['sample_identifier_type'] = metaDataDict['sample_identifier_type']
    # dataTableDF['timepoint'] = ''
    # dataTableDF['annot_1'] = ''
    dataTableDF['annot_2'] = ''
    dataTableDF['annot_3'] = ''

    print('dataLabelList:', dataLabelList)
    print('dataTableDF:', dataTableDF.head(5))

    rtiDF_transposed, outputAssayDataFileName = svc.set_up_data_export_for_rti(dataTableDF, documentName, dataLabelList)
    rtiDF_transposed.drop(rtiDF_transposed.tail(1).index, inplace=True)
    # rtiDF_transposed = rtiDF_transposed.iloc[:, -1]
    # print('rtiDF_transposed:', rtiDF_transposed.iloc[:, 1])

    print(f"Saving {outputAssayDataFileName} file.")
    print('rtiDF_transposed:', rtiDF_transposed.head(5))
    print('rtiDF_transposed:', rtiDF_transposed.tail(5))
    rtiDF_transposed.to_csv(data_folder + 'supplementary_data/' + outputAssayDataFileName, sep="\t", header=False)


def export_data_for_rti():
    print(f' ***************     Export data for import into mapMECFS     *************** ')

    dataTableDF, data_file_name, metaDataDict, documentName, fastLoad = \
        import_custom_assay_data()
    dataTableDF.drop('unique_id', axis=1, inplace=True)
    dataTableDF.drop('data_file_name', axis=1, inplace=True)
    dataTableDF['timepoint'] = dataTableDF['timepoint'].astype(str)

    # print('metaDataDict:', metaDataDict)
    # print('dataTableDF:', dataTableDF.head())
    # print('dataTableDF.columns:', dataTableDF.columns)

    # Set up summary phenotype dataframe
    columns = ['phenotype', 'biospecimen_type'] + set_up_globals.exportAssayColumnsForRTI
    modifiedColumns = modify_df_column_names(columns)
    df = pd.DataFrame(columns=modifiedColumns)

    for index, row in dataTableDF.iterrows():
        study_id = row['ENID']
        # print('index, row:', index, row)
        clinical_data_list = svc.find_clinical_data_by_study_id(study_id)
        # print('clinical_data_list:', clinical_data_list.phenotype)
        df.loc[len(df.index)] = [clinical_data_list.phenotype,
                                metaDataDict['biospecimen_type'],
                                clinical_data_list.cor_id,
                                row['timepoint'],
                                metaDataDict['sample_identifier_type'], '', '', '']

    rti_phenotype_DF, outputPhenotypeFileName = svc.set_up_phenotype_export_for_rti(df, documentName.replace(' ', '_'))

    print(f"There are {len(rti_phenotype_DF)} summary rows.")
    # print(rti_phenotype_DF.head(5))
    # print(rti_phenotype_DF.columns)

    # Save summary file
    rti_phenotype_DF.to_csv(data_folder + 'supplementary_data/' + outputPhenotypeFileName, sep="\t")

    # Set up assay data dataframe
    dataLabelList = list(dataTableDF.columns[6:])
    # dataTableDF['cor_id'] = ''
    dataTableDF['sample_identifier_type'] = metaDataDict['sample_identifier_type']
    # dataTableDF['timepoint'] = ''
    dataTableDF['annot_1'] = ''
    dataTableDF['annot_2'] = ''
    dataTableDF['annot_3'] = ''

    for index, row in dataTableDF.iterrows():
        study_id = row['ENID']
        clinical_data_list = svc.find_clinical_data_by_study_id(study_id)
        # print('clinical_data_list:', clinical_data_list.phenotype)
        dataTableDF.loc[index, 'cor_id'] = clinical_data_list.cor_id

    # dataTableDF.drop('AnalysisID', axis=1, inplace=True)
    # dataTableDF.drop('ENID', axis=1, inplace=True)

    # print('dataLabelList:', dataLabelList)
    # print('dataTableDF:', dataTableDF.head(5))
    # print('dataTableDF["cor_id"]:', dataTableDF['cor_id'].head(5))
    # print('dataTableDF["timepoint"]:', dataTableDF["timepoint"].head(5))
    # print('duplicate index:', dataTableDF[dataTableDF.duplicated(['cor_id', 'timepoint'])])
    # print('is_unique:', dataTableDF.index.is_unique)

    rtiDF_transposed, outputAssayDataFileName = svc.set_up_data_export_for_rti(dataTableDF, 'ev_proteomics_brc', dataLabelList)
    rtiDF_transposed.drop(rtiDF_transposed.tail(1).index, inplace=True)

    print(f"Saving {outputAssayDataFileName} file.")
    print('rtiDF_transposed:', rtiDF_transposed.head(5))
    print('rtiDF_transposed:', rtiDF_transposed.tail(5))
    rtiDF_transposed.to_csv(data_folder + 'supplementary_data/' + outputAssayDataFileName, sep="\t", header=False)


def export_ev_proteomics_brc_for_rti():
    print(f' ***************     Export EV Proteomics BRC data for import into mapMECFS     *************** ')

    dataTableDF, data_file_name, metaDataDict, documentName, fastLoad = \
        import_custom_assay_data()
    dataTableDF.drop('unique_id', axis=1, inplace=True)
    dataTableDF.drop('data_file_name', axis=1, inplace=True)
    dataTableDF['timepoint'] = dataTableDF['timepoint'].astype(str)

    print('metaDataDict:', metaDataDict)
    print('dataTableDF:', dataTableDF.head())
    print('dataTableDF.columns:', dataTableDF.columns)

    # Set up summary phenotype dataframe
    columns = ['phenotype', 'biospecimen_type'] + set_up_globals.exportAssayColumnsForRTI
    modifiedColumns = modify_df_column_names(columns)
    df = pd.DataFrame(columns=modifiedColumns)

    for index, row in dataTableDF.iterrows():
        study_id = row['ENID']
        # print('index, row:', index, row)
        clinical_data_list = svc.find_clinical_data_by_study_id(study_id)
        # print('clinical_data_list:', clinical_data_list.phenotype)
        df.loc[len(df.index)] = [clinical_data_list.phenotype,
                                metaDataDict['biospecimen_type'],
                                clinical_data_list.cor_id,
                                row['timepoint'],
                                metaDataDict['sample_identifier_type'], '', '', '']

    rti_phenotype_DF, outputPhenotypeFileName = svc.set_up_phenotype_export_for_rti(df, 'ev_proteomics_brc')
    # rti_phenotype_DF.rename(columns={'cor_id': 'pub_id'}, inplace=True)

    print(f"There are {len(rti_phenotype_DF)} summary rows.")
    print(rti_phenotype_DF.head(5))
    print(rti_phenotype_DF.columns)

    # Save summary file
    rti_phenotype_DF.to_csv(data_folder + 'supplementary_data/' + outputPhenotypeFileName, sep="\t")

    # Set up assay data dataframe
    dataLabelList = list(dataTableDF.columns[6:])
    # dataTableDF['cor_id'] = ''
    dataTableDF['sample_identifier_type'] = metaDataDict['sample_identifier_type']
    # dataTableDF['timepoint'] = ''
    dataTableDF['annot_1'] = ''
    dataTableDF['annot_2'] = ''
    dataTableDF['annot_3'] = ''

    for index, row in dataTableDF.iterrows():
        study_id = row['ENID']
        clinical_data_list = svc.find_clinical_data_by_study_id(study_id)
        # print('clinical_data_list:', clinical_data_list.phenotype)
        dataTableDF.loc[index, 'cor_id'] = clinical_data_list.cor_id

    # dataTableDF.drop('AnalysisID', axis=1, inplace=True)
    # dataTableDF.drop('ENID', axis=1, inplace=True)

    print('dataLabelList:', dataLabelList)
    print('dataTableDF:', dataTableDF.head(5))
    print('dataTableDF["cor_id"]:', dataTableDF['cor_id'].head(5))
    print('dataTableDF["timepoint"]:', dataTableDF["timepoint"].head(5))
    print('duplicate index:', dataTableDF[dataTableDF.duplicated(['cor_id', 'timepoint'])])
    print('is_unique:', dataTableDF.index.is_unique)

    rtiDF_transposed, outputAssayDataFileName = svc.set_up_data_export_for_rti(dataTableDF, 'ev_proteomics_brc', dataLabelList)
    rtiDF_transposed.drop(rtiDF_transposed.tail(1).index, inplace=True)

    print(f"Saving {outputAssayDataFileName} file.")
    print('rtiDF_transposed:', rtiDF_transposed.head(5))
    print('rtiDF_transposed:', rtiDF_transposed.tail(5))
    rtiDF_transposed.to_csv(data_folder + 'supplementary_data/' + outputAssayDataFileName, sep="\t", header=False)


def export_ev_pilot_study_for_rti():
    print(f' ***************     Export EV pilot study data for import into mapMECFS     *************** ')

    dataTableDF, data_file_name, metaDataDict, documentName, fastLoad = \
        import_custom_assay_data()
    dataTableDF.drop('unique_id', axis=1, inplace=True)
    dataTableDF.drop('data_file_name', axis=1, inplace=True)
    # dataTableDF['timepoint'] = dataTableDF['timepoint'].astype(str)

    print('metaDataDict:', metaDataDict)
    print('dataTableDF:', dataTableDF.head())
    print('dataTableDF.columns:', dataTableDF.columns)

    # # Set up summary phenotype dataframe
    # columns = ['phenotype', 'biospecimen_type'] + set_up_globals.exportAssayColumnsForRTI
    # modifiedColumns = modify_df_column_names(columns)
    # df = pd.DataFrame(columns=modifiedColumns)
    #
    # for index, row in dataTableDF.iterrows():
    #     pub_id = row['pub_id']
    #     clinical_data_list = svc.find_clinical_data_by_pub_id(pub_id)
    #     # print('clinical_data_list:', clinical_data_list.phenotype)
    #     df.loc[len(df.index)] = [clinical_data_list.phenotype,
    #                             metaDataDict['biospecimen_type'],
    #                             pub_id, row['timepoint'], metaDataDict['sample_identifier_type'], '', '', '']
    #
    # rti_phenotype_DF, outputPhenotypeFileName = svc.set_up_phenotype_export_for_rti(df, documentName.replace(' ', '_'))
    # rti_phenotype_DF.rename(columns={'cor_id': 'pub_id'}, inplace=True)
    #
    # print(f"There are {len(rti_phenotype_DF)} summary rows.")
    # print(rti_phenotype_DF.head(5))
    # print(rti_phenotype_DF.columns)
    #
    # # Save summary file
    # rti_phenotype_DF.to_csv(data_folder + 'supplementary_data/' + outputPhenotypeFileName, sep="\t")

    # Set up assay data dataframe
    dataLabelList = list(dataTableDF.columns[5:])
    dataTableDF['cor_id'] = dataTableDF['study_id']
    dataTableDF['sample_identifier_type'] = metaDataDict['sample_identifier_type']
    # dataTableDF['timepoint'] = ''
    dataTableDF['annot_1'] = ''
    dataTableDF['annot_2'] = ''
    dataTableDF['annot_3'] = ''

    print('dataLabelList:', dataLabelList)
    print('dataTableDF:', dataTableDF.head(5))

    rtiDF_transposed, outputAssayDataFileName = svc.set_up_data_export_for_rti(dataTableDF, documentName, dataLabelList)
    rtiDF_transposed.drop(rtiDF_transposed.tail(1).index, inplace=True)

    print(f"Saving {outputAssayDataFileName} file.")
    print('rtiDF_transposed:', rtiDF_transposed.head(5))
    print('rtiDF_transposed:', rtiDF_transposed.tail(5))
    rtiDF_transposed.to_csv(data_folder + 'supplementary_data/' + outputAssayDataFileName, sep="\t", header=False)


def import_custom_assay_data(custom_sheet_name='Data Table', personIdentifierColumn='ENID'):
    # Look up file
    items = os.listdir(data_folder)
    fileList = []
    for names in items:
        if (names.endswith('.xlsx') or names.endswith('.xls')) and not names.startswith('~'):
            fileList.append(names)

    for idx, fileName in enumerate(fileList):
        print('{}. {}'.format(
            idx + 1,
            fileName
        ))

    message = f"\nPlease select a file number between 1 and {str(len(fileList))}: "
    response = input(message)
    # //--- need some error checking here
    # if response in set_up_globals.exitResponseList:
    #     return  # None, None

    try:
        data_file_name = fileList[int(response) - 1]
    except (IndexError, ValueError):
        error_msg('\nError: You did not make a valid file selection \n')
        return  # None, None

    # Start by reading metadata sheet
    # Need to know: documentName, index_column, sheet_name, and skiprows before reading data sheet
    metaDataDict = {'submitter_name': None,
                    'submitter_netid': None,
                    'pi_name': None,
                    'unique_assay_name': None,
                    'assay_type': None,
                    'assay_method': None,
                    'biospecimen_type': None,
                    'sample_identifier_type': None,
                    'dataset_name': None,
                    'dataset_annotation': None,
                    'data_label_type': None,
                    'comment': None,
                    'units': None,
                    'normalization_method': None,
                    'pipeline': None,
                    'title': None,
                    'description': None,
                    'tags': None,
                    'organization': None,
                    'current_visibility': None,
                    'data_type': None,
                    'organism': None,
                    'assay': None,
                    'measurement': None,
                    'study_type': None,
                    'sample': None,
                    'file_name_location': None,
                    }
    engine = 'openpyxl'  # Support for xlxs file format
    if data_file_name.split('.')[1] == 'xls':
        engine = 'xlrd'  # Support for xls file format
    skiprows = range(0, 3)
    metaDataDF = pd.read_excel(data_folder + data_file_name,
                               sheet_name='Metadata', skiprows=skiprows, engine=engine, keep_default_na=False)
    for i, row in metaDataDF.iterrows():
        metaDataType = modify_df_column_names([str(row[0]).lower()])[0]
        response = str(row[1])
        if metaDataType in metaDataDict and len(response.strip()) > 0 and response.strip().lower() != 'nan':
            metaDataDict[metaDataType] = response.strip()

    # Display what was just read
    print('')
    for key, val in metaDataDict.items():
        print(key, ':', val)

    # Check assay type
    # //--- replace all these with global references
    validAssayTypes = [set_up_globals.proteomics_document_name,
                       set_up_globals.cytokines_document_name,
                       set_up_globals.metabolomics_document_name,
                       set_up_globals.mirnaseq_document_name,
                       set_up_globals.scrnaseq_document_name,
                       set_up_globals.seahorse_document_name,
                       set_up_globals.cpet_recovery_document_name,
                       'BDNF',
                       'CPET',
                       'LPS',
                       'Other']
    documentName = metaDataDict['assay_type']
    if documentName not in validAssayTypes:
        error_msg(f'Error: {documentName} is not a valid assay type')
        error_msg('Exiting data load')
        return  # None, None

    # If separate file specified, check that it exists
    externalFileName = ''
    if metaDataDict['file_name_location'] is not None:
        externalFileName = data_folder + metaDataDict['file_name_location']
        if not exists(externalFileName):
            error_msg(f'Error: {externalFileName} does not exist')
            error_msg('Exiting data load')
            return  # None, None

    message = f"\nIs this correct? (y/n): "
    response = input(message)
    if response[0].lower() != 'y':
        return  # None, None

    print(f' ******************** Import {documentName} data ******************** ')

    # If link to file exists, read data from there, otherwise read data from 'Data Table' tab of spreadsheet
    if len(externalFileName) == 0:  # Read data from 'Data Table' tab
        skiprows = range(0, 1)  # //--- for now, define skiprows as the top row - can adjust this later
        df = pd.read_excel(data_folder + data_file_name,
                           sheet_name=custom_sheet_name, skiprows=skiprows, engine=engine, keep_default_na=False)
    else:  # Read data from external file
        df = pd.read_csv(externalFileName, sep='\t', header=0, keep_default_na=False)

    # Remove nulls from ENID
    print('df:', df.head())
    index_names = df[df[personIdentifierColumn] == ''].index
    df.drop(index_names, inplace=True)

    # Remove unnamed columns
    unnamedColList = [colName for colName in df.columns if str(colName).startswith('Unnamed')]
    df.drop(labels=unnamedColList, axis='columns', inplace=True)

    # Get column names
    classColumnList = utilities.attributes(AssayMetaData)
    df.columns = modify_df_column_names(df.columns, classColumnList)

    # Create custom columns
    create_custom_columns(df, documentName, data_file_name, metaDataDict['sample_identifier_type'])

    print('df:', df['unique_id'].head())
    try:
        df.set_index('unique_id', drop=False, inplace=True, verify_integrity=True)
    except (ValueError, ValidationError) as e:
        message = f'Create of index for {documentName} data resulted in exception: {e}'
        error_msg(message)
        error_msg('No data saved')
        return  # Skip the rest of this function

    # Fast load: assumes that all assay data in new and aso skips the reference to the biospecimen
    fastLoad = False
    if documentName == set_up_globals.scrnaseq_document_name: fastLoad = True

    return df, data_file_name, metaDataDict, documentName, fastLoad


def generate_demo_data():
    # Set up random demo data for demographic and assay tables
    dictionaryLists = {
        'site': ['ITH', 'LA', 'NYC'],
        'sex': ['M', 'F'],
        'phenotype': ['ME/CFS', 'HC'],
        'ethnicity': ['1', '2', '3', 'NA'],
        'race': ['1', '2', '3', '4', '5', '6', 'NA'],
        'mecfs_sudden_gradual': ['1', '2'],
        'qmep_sudevent': ['1', '2', '3', '4', '5', '6', '7', '8'],
    }

    annot_1 = ['4', '10', '14', '21', '23', '24']
    annot_2 = ['batch1', 'batch2', 'batch3', 'batch4', 'batch5', 'batch6', 'batch7', 'batch8', 'batch9', 'batch10']

    symbolLists = {
        'Proteomics': ['Gene_A', 'Gene_B', 'Gene_C', 'Gene_D', 'Gene_E', 'Gene_F', 'Gene_G', 'Gene_H',
                       'Gene_I', 'Gene_J', 'Gene_K', 'Gene_L', 'Gene_M', 'Gene_N', 'Gene_O'],
        'Cytokines': ['Label_1', 'Label_2', 'Label_3', 'Label_4', 'Label_5', 'Label_6', 'Label_7', 'Label_8',
                      'Label_9', 'Label_10', 'Label_11', 'Label_12', 'Label_13', 'Label_14', 'Label_15', 'Label_16',
                      'Label_17', 'Label_18', 'Label_19', 'Label_20', 'Label_21', 'Label_22', 'Label_23', 'Label_24',
                      'Label_25', 'Label_26', 'Label_27', 'Label_28', 'Label_29', 'Label_30', 'Label_31', 'Label_32',
                      'Label_33', 'Label_34', 'Label_35', 'Label_36', 'Label_37', 'Label_38', 'Label_39', 'Label_40'],
        'Metabolomics': ['Compound_1', 'Compound_2', 'Compound_3', 'Compound_4', 'Compound_5', 'Compound_6',
                         'Compound_7', 'Compound_8',
                         'Compound_9', 'Compound_10', 'Compound_11', 'Compound_12', 'Compound_13', 'Compound_14',
                         'Compound_15', 'Compound_16',
                         'Compound_17', 'Compound_18', 'Compound_19', 'Compound_20', 'Compound_21', 'Compound_22',
                         'Compound_23', 'Compound_24',
                         'Compound_25', 'Compound_26', 'Compound_27', 'Compound_28', 'Compound_29', 'Compound_30',
                         'Compound_31', 'Compound_32',
                         'Compound_33', 'Compound_34', 'Compound_35', 'Compound_36', 'Compound_37', 'Compound_38',
                         'Compound_39', 'Compound_40'],
        'scRNAseq': ['Gene_A', 'Gene_B', 'Gene_C', 'Gene_D', 'Gene_E', 'Gene_F', 'Gene_G', 'Gene_H',
                     'Gene_I', 'Gene_J', 'Gene_K', 'Gene_L', 'Gene_M', 'Gene_N', 'Gene_O'],
        'miRNAseq': ['has_let_1A_3p', 'has_let_1A_5p', 'has_let_1B_3p', 'has_let_1B_5p',
                     'has_let_1A_3p', 'has_let_1A_5p', 'has_let_1A_3p', 'has_let_1A_5p',
                     'has_let_1C_3p', 'has_let_1C_5p', 'has_let_1D_3p', 'has_let_1D_5p',
                     'has_let_1E_3p', 'has_let_1E_5p', 'has_let_1F_3p', 'has_let_1F_5p'],
    }

    columns = ['study_id', 'site', 'phenotype', 'age', 'height_in', 'weight_lbs', 'bmi', 'ethnicity', 'race',
               'mecfs_sudden_gradual', 'qmep_sudevent', 'mecfs_duration']
    integerFieldList, floatFieldList, decimalFieldList, longFieldList = utilities.get_numeric_attributes(ClinicalData)
    naList = ['vo2change', 'at1', 'at2', 'atchange', 'qmep_lived', 'q_medications', 'q_lastantibiotic',
              'q_lastantibiotic_details', 'q_supplements', 'pahq_activitylist', 'hh24hr_eaten_d1',
              'hh24hr_coffeetea_d1', 'hh24hr_smoke_d1', 'hh24hr_alcohol_d1', 'hh24hr_blood_d1', 'hh24hr_illness_d1',
              'hh24hr_respiratory_d1', 'hh24hr_medication_d1', 'hh24hr_peyesterday_d1', 'hh24hr_petoday_d1',
              'hh24hr_eaten_d2', 'hh24hr_coffeetea_d2', 'hh24hr_smoke_d2', 'hh24hr_alcohol_d2', 'hh24hr_blood_d2',
              'hh24hr_illness_d2', 'hh24hr_respiratory_d2', 'hh24hr_medication_d2', 'hh24hr_peyesterday_d2',
              'hh24hr_petoday_d2', 'qmep_mediagnosis', 'qmep_mesymptoms', 'qmep_metimediagnosis', 'cpet_d1',
              'cpet_d2'] + integerFieldList + floatFieldList
    for item in columns:
        if item in naList: naList.remove(item)

    columns = columns + naList
    columns = list(dict.fromkeys(columns))

    documentName = set_up_globals.clinical_document_name
    success_msg(f'Generating {documentName} data.')
    output_data_file_name = documentName + '_demo_data.xlsx'
    df = pd.DataFrame(columns=columns)

    numberOfPeople = 80
    for enid in range(1000, 1001 + numberOfPeople):
        data = {'study_id': 'ENID' + str(enid)}
        for naItem in naList:
            data[naItem] = 'NA'
        for dictItem in dictionaryLists:
            if dictItem == 'mecfs_sudden_gradual' or dictItem == 'qmep_sudevent':
                if data['phenotype'] == 'ME/CFS':
                    data[dictItem] = sample(dictionaryLists[dictItem], 1)[0]
                else:
                    data[dictItem] = 'NA'
            else:
                data[dictItem] = sample(dictionaryLists[dictItem], 1)[0]
        data['age'] = randint(18, 75)
        data['height_in'] = randint(60, 76)
        data['weight_lbs'] = randint(95, 260)
        data['bmi'] = uniform(19, 40)
        if data['phenotype'] == 'ME/CFS':
            data['mecfs_duration'] = randint(1, 36)
        else:
            data['mecfs_duration'] = 'NA'
        for naItem in naList:
            data[naItem] = 'NA'

        df = df.append(data, ignore_index=True)

    with pd.ExcelWriter(data_folder + output_data_file_name) as writer:
        df.to_excel(writer, sheet_name='Data Table', index=False, startrow=0)

    for documentName in [set_up_globals.proteomics_document_name, set_up_globals.cytokines_document_name,
                         set_up_globals.metabolomics_document_name, set_up_globals.scrnaseq_document_name,
                         set_up_globals.mirnaseq_document_name]:

        success_msg(f'Generating {documentName} data.')

        output_data_file_name = documentName + '_demo_data.xlsx'
        symbolList = symbolLists[documentName]
        df = pd.DataFrame(columns=['AnalysisID', 'ENID', 'Timepoint', 'Annot-1', 'Annot-2', 'Annot-3'] + symbolList)
        rowNumber = 0

        for enid in range(1000, 1001 + numberOfPeople):
            for Timepoint in ['Pre-Day1', 'Post-Day1', 'Pre-Day2']:
                rowNumber += 1
                data = {'AnalysisID': rowNumber, 'ENID': enid, 'Timepoint': Timepoint,
                        'Annot-1': sample(annot_1, 1)[0], 'Annot-2': sample(annot_2, 1)[0], 'Annot-3': ''}
                for sym in symbolList:
                    data[sym] = random()
                df = df.append(data, ignore_index=True)

        with pd.ExcelWriter(data_folder + output_data_file_name, mode='a') as writer:
            df.to_excel(writer, sheet_name='Data Table', index=False, startrow=1)


def calculate_pathway_summaries():
    print(' ********************     Calculate gene pathway summaries     ******************** ')

    # Get a list of all the subjects in the database
    clinicalDataObjectList = svc.find_clinical_data()

    # Get list of gene pathways
    genePathwayList = svc.find_data_label_pathway_list()

    # Get list of unique assay names
    uniqueAssayList = svc.find_unique_assay_names()

    pathwayCounter = 0
    pathwayTotal = len(genePathwayList)
    for pathwayObject in genePathwayList:
        # for idx, c in enumerate(pathwayObject.data_label_references):
        #     print(' {}. {}: {}'.format(idx + 1, c.data_label, c.gene_symbol_references[0].data_label))

        df, dataGeneSymbolList = utilities.create_df_from_object_list(clinicalDataObjectList,
                                                                      [AssayMetaData],
                                                                      ['assay_meta_data'],
                                                                      uniqueAssayList,
                                                                      assayResultsFlag=True,
                                                                      assaySummaryFlag=False,
                                                                      dataLabelPathwayIDs=pathwayObject)

        pathwayCounter += 1
        print('Pathway name: %s (%s of %s)' % (pathwayObject.pathway_name, str(pathwayCounter), str(pathwayTotal)))
        print('dataGeneSymbolList:', dataGeneSymbolList)
        # print(df.head(5))
        # print(df.columns)
        print(f"There are {len(df)} records.")

        # Calculate summaries
        for summaryType in set_up_globals.summary_type_choices:
            df[summaryType] = None

        for idx, c in df.iterrows():

            # print(' {}. {}: {}'.format(idx + 1, c.study_id,
            #                            'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'))
            # print('      * Assay summary: {}, {}'.format(c.unique_assay_name, c.timepoint))
            arList = []
            for ar in dataGeneSymbolList:
                # print('            * Results: {}, {}'.format(ar, c[ar]))
                if not np.isnan(c[ar]):
                    arList.append(c[ar])
            # print(np.ma.average(arList))
            if not np.isnan(np.ma.average(arList)):
                df.loc[idx, 'Average'] = np.ma.average(arList)

            # //--- Add other summaries here - GSEA next!

        # Save summary values back to the clinical data object
        print(df.head(15))
        svc.save_assay_summary_data(state.active_account, pathwayObject.pathway_name, df)


def test_pathway_mapping():
    print(' ********************     Test pathway mapping     ******************** ')

    pathway_name = 'Cytokine / proteomic test'
    dataLabelPathwayIDs = svc.find_data_label_pathway_reference(pathway_name)

    for idx, c in enumerate(dataLabelPathwayIDs.data_label_references):
        print(' {}. {}: {}'.format(idx + 1, c.data_label, c.gene_symbol_references[0].data_label))

    data_list = svc.test_pathway_mapping()
    df, dataGeneSymbolList = utilities.create_df_from_object_list(data_list,
                                                                  [AssayMetaData],
                                                                  ['assay_meta_data'],
                                                                  ['Cytokine Plasma MFI', 'Cytokine EV MFI',
                                                                   'Proteomics EV'],
                                                                  assayResultsFlag=True,
                                                                  dataLabelPathwayIDs=dataLabelPathwayIDs)

    print('dataGeneSymbolList:', dataGeneSymbolList)
    print(df.head(15))
    print(df.columns)

    print(f"There are {len(df)} records.")
    df['aggregated_result'] = 0
    for idx, c in df.iterrows():
        print(' {}. {}: {}'.format(idx + 1, c.study_id,
                                   'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'))
        print('      * Assay summary: {}, {}'.format(c.unique_assay_name, c.timepoint))
        arList = []
        for ar in dataGeneSymbolList:
            if not np.isnan(c[ar]):
                arList.append(c[ar])
            print('            * Results: {}, {}'.format(ar, c[ar]))
        print(np.ma.average(arList))
        df.loc[idx, 'aggregated_result'] = np.ma.average(arList)

    print(df.head(15))

    # results_ave = svc.test_pathway_average(dataLabelPathwayIDs)
    # print('results_ave:', results_ave)


def list_clinical_data(suppress_header=False):
    if not suppress_header:
        print(
            f' ********************     {set_up_globals.clinical_document_name.capitalize()} data     ******************** ')

    clinical_data_list = svc.find_clinical_data()
    print(f"There are {len(clinical_data_list)} records.")
    for idx, c in enumerate(clinical_data_list):
        print(' {}. {}: {}'.format(idx + 1, c.study_id,
                                   'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'))
        for sc in c.scrnaseq_summary:
            print('      * scRNA-seq summary: {}, {}'.format(
                sc.brc_id,
                sc.sample_name
            ))


def list_biospecimen_data_for_study_id():
    list_clinical_data(suppress_header=True)

    study_id = input("Enter study ID: ")
    if not study_id.strip():
        error_msg('Cancelled')
        print()
        return

    study_id = int(study_id)
    biospecimen_data_list = svc.find_biospecimen_data_by_study_id(study_id)

    print("There are {} biospecimens for study ID {}.".format(len(biospecimen_data_list), study_id))
    print(biospecimen_data_list)
    for idx, b in enumerate(biospecimen_data_list):
        print(' {}. Date received: {}, Tube number: {}, Freezer ID: {}'.format(idx + 1, b.date_received, b.tube_number,
                                                                               b.freezer_id))
        # for sc in c.scrnaseq_summary:
        #     print('      * scRNA-seq summary: {}, {}'.format(
        #         sc.brc_id,
        #         sc.sample_name
        #     ))


def list_biospecimen_data_for_scrnaseq_summary():
    print(' ********************     Biospecimen data for scRNA-seq summaries     ******************** ')

    list_clinical_data(suppress_header=True)

    study_id = input("Enter study ID: ")
    if not study_id.strip():
        error_msg('Cancelled')
        print()
        return

    study_id = int(study_id)
    clinical_data_list = svc.find_clinical_data_by_study_id(study_id)
    print('Study ID: {} - {}'.format(
        clinical_data_list.study_id,
        'ME/CFS patient' if clinical_data_list.phenotype == 'ME/CFS' else 'Healthy control'))
    if clinical_data_list.scrnaseq_summary.count() < 1:
        print(f'No scRNA-seq summary records for study ID {str(study_id)}')
        return
    for sc in clinical_data_list.scrnaseq_summary:
        print(
            '      * scRNA-seq summary: , Sample name: {}, Tube number: {}, Freezer ID: {}, Date received: {}'.format(
                sc.sample_name,
                sc.biospecimen_data_reference.tube_number,
                sc.biospecimen_data_reference.freezer_id,
                sc.biospecimen_data_reference.date_received
            ))


def list_only_scrnaseq_summary():
    print(' ********************     Only scRNA-seq summaries     ******************** ')

    scrnaseq_summary_data_list = svc.find_only_scrnaseq_summary_data()
    if scrnaseq_summary_data_list is None:
        print(f'No scRNA-seq summary records.')
        return

    for c in scrnaseq_summary_data_list:
        print('Study ID: {} - {}'.format(
            c.study_id,
            'ME/CFS patient' if c.phenotype == 'ME/CFS' else 'Healthy control'))
        for sc in c.scrnaseq_summary:
            print(
                '      Sample: {}, Freezer ID: {}, {} {} {} {}'.format(
                    sc['sample_name'],
                    sc.biospecimen_data_reference.freezer_id,
                    sc.number_of_reads,
                    sc.estimated_number_of_cells,
                    sc.mean_reads_per_cell,
                    sc.median_genes_per_cell
                ))


def exit_app():
    print()
    print('bye')
    raise KeyboardInterrupt()


def get_action():
    text = '> '
    if state.active_account:
        text = f'{state.active_account.name}> '

    action = input(Fore.YELLOW + text + Fore.WHITE)
    return action.strip().lower()


def unknown_command():
    print("Sorry we didn't understand that command.")


def success_msg(text):
    print(Fore.LIGHTGREEN_EX + text + Fore.WHITE)


def error_msg(text):
    print(Fore.LIGHTRED_EX + text + Fore.WHITE)


def print_header():
    print(Fore.WHITE + '*********************************************')
    print(Fore.GREEN + '              ME/CFS Import')
    print(Fore.WHITE + '*********************************************')
    print()


if __name__ == '__main__':
    main()
