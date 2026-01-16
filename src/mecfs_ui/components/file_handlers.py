import pandas as pd
import os
from typing import Tuple
from io import StringIO

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import services.data_service as svc
import set_up_globals
import utilities


def modify_df_column_names(column_names, classColumnList=None):
    """
    Normalize column names using utilities.modify_string.
    Matches logic from program_actions.py.
    """
    renamed_columns = []
    for i in range(len(column_names)):
        original_col = str(column_names[i]).strip()
        col = utilities.modify_string(original_col)

        # If classColumnsList exists then restrict column names to only those in the class
        # This prevents the changing of gene symbols that are included as columns in the Excel spreadsheet
        if (classColumnList is not None) and (col not in classColumnList):
            renamed_columns.append(original_col)
        else:
            renamed_columns.append(col)

    return renamed_columns


def create_custom_columns(df, documentName, data_file_name, index_column=None):
    """
    Create custom columns based on document type.
    Matches logic from program_actions.py.
    """
    df['data_file_name'] = data_file_name

    if documentName == set_up_globals.scrnaseq_summary_document_name:
        df['study_id'] = df['enid']

    if documentName in [set_up_globals.proteomics_document_name,
                        set_up_globals.cytokines_document_name,
                        set_up_globals.metabolomics_document_name,
                        set_up_globals.mirnaseq_document_name,
                        set_up_globals.scrnaseq_document_name,
                        'CPET',
                        set_up_globals.cpet_recovery_document_name,
                        'Other']:
        df['study_id'] = df['ENID']

        validTimePoints = ['D1-PRE', 'D1-POST', 'D2-PRE', 'D2-POST', 'Other', '0h', '15min', '24h', 'D1', 'D2']
        timepoint_list = []
        for val in df['timepoint']:
            if val in validTimePoints:
                timepoint_list.append(val)
            elif str(val).lower() == 'pre-day1':
                timepoint_list.append('D1-PRE')
            elif str(val).lower() == 'post-day1':
                timepoint_list.append('D1-POST')
            elif str(val).lower() == 'pre-day2':
                timepoint_list.append('D2-PRE')
            elif str(val).lower() == 'post-day2':
                timepoint_list.append('D2-POST')
            else:
                timepoint_list.append('')
        df['timepoint'] = timepoint_list

        # Set up unique_id column
        if index_column == 'AnalysisID':
            index_names = df[df[index_column] == ''].index
            df.drop(index_names, inplace=True)
            df['unique_id'] = df[index_column]
        elif index_column == 'ENID+Timepoint':
            unique_id_list = []
            for index, row in df.iterrows():
                unique_id_list.append(svc.convert_to_string(row.study_id) + '-' + row.timepoint + '-' + data_file_name)
            df['unique_id'] = unique_id_list
        elif index_column == 'ENID+Timepoint+Annot-1':
            unique_id_list = []
            for index, row in df.iterrows():
                unique_id_list.append(svc.convert_to_string(row.study_id) + '-' + row.timepoint + '-' + str(
                    row.annot_1) + '-' + data_file_name)
            df['unique_id'] = unique_id_list
        elif index_column == 'ENID+Timepoint+Annot-1+Annot-2':
            unique_id_list = []
            for index, row in df.iterrows():
                unique_id_list.append(svc.convert_to_string(row.study_id) + '-' + row.timepoint + '-' +
                                      str(row.annot_1) + '-' + str(row.annot_2) + '-' + data_file_name)
            df['unique_id'] = unique_id_list

    if documentName == set_up_globals.biospecimen_document_name:
        df['sample_id'] = df['id']
        # Set Specimen ID to ENID, CPET Day, Pre/Post, and Specimen type
        specimen_id_list = []
        for val in df['specimen_id']:
            valMinusTubeNumberList = str(val).split('-')[0:4]
            specimen_id_list.append('-'.join(valMinusTubeNumberList))
        df['specimen_id'] = specimen_id_list

    if documentName == set_up_globals.clinical_document_name:
        # Make sure study ID is numeric (i.e. strip off 'ENID' if it exists)
        study_id_list = [int(str(val).strip('ENID')) for val in df['study_id']]
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

    if documentName == set_up_globals.seahorse_document_name:
        df['unique_id'] = df[index_column]

    if documentName == set_up_globals.cpet_recovery_document_name:
        df['pub_id'] = df['ENID']

    if documentName == set_up_globals.ev_pilot_study_document_name:
        df['unique_id'] = df['ENID']


def process_clinical_data_file(file_path: str, user) -> Tuple[bool, str]:
    """
    Process clinical data Excel file and import to database.

    Returns:
        Tuple of (success: bool, log_messages: str)
    """
    log = StringIO()

    try:
        # Determine engine based on file extension
        ext = os.path.splitext(file_path)[1].lower()
        engine = 'xlrd' if ext == '.xls' else 'openpyxl'

        # Read Excel file
        df = pd.read_excel(file_path, engine=engine, keep_default_na=False)

        # Normalize column names
        df.columns = modify_df_column_names(df.columns)

        # Remove rows with empty study_id
        index_column = 'study_id'
        if index_column not in df.columns:
            log.write(f"Error: Required column 'study_id' not found in file\n")
            return False, log.getvalue()

        index_names = df[df[index_column] == ''].index
        df.drop(index_names, inplace=True)

        # Add missing required columns with empty values
        # These are expected by add_clinical_data in data_service.py
        required_columns = [
            'cu_id', 'cor_id', 'pub_id', 'site', 'sex', 'phenotype',
            'ethnicity', 'race', 'mecfs_sudden_gradual', 'qmep_sudevent',
            'qmep_mediagnosis', 'qmep_mesymptoms', 'qmep_metimediagnosis',
            'cpet_d1', 'cpet_d2', 'vo2change', 'atchange',
            'qmep_lived', 'q_medications', 'q_lastantibiotic',
            'q_lastantibiotic_details', 'q_supplements', 'pahq_activitylist',
            'hh24hr_eaten_d1', 'hh24hr_coffeetea_d1', 'hh24hr_smoke_d1',
            'hh24hr_alcohol_d1', 'hh24hr_blood_d1', 'hh24hr_illness_d1',
            'hh24hr_respiratory_d1', 'hh24hr_medication_d1',
            'hh24hr_peyesterday_d1', 'hh24hr_petoday_d1',
            'hh24hr_eaten_d2', 'hh24hr_coffeetea_d2', 'hh24hr_smoke_d2',
            'hh24hr_alcohol_d2', 'hh24hr_blood_d2', 'hh24hr_illness_d2',
            'hh24hr_respiratory_d2', 'hh24hr_medication_d2',
            'hh24hr_peyesterday_d2', 'hh24hr_petoday_d2',
        ]

        # Add binned columns from config
        for bin_col in set_up_globals.binnedColumnsDict.keys():
            if bin_col not in required_columns:
                required_columns.append(bin_col)

        for col in required_columns:
            if col not in df.columns:
                df[col] = ''

        # Create custom columns (data_file_name, etc.)
        data_file_name = os.path.basename(file_path)
        create_custom_columns(df, set_up_globals.clinical_document_name, data_file_name)

        # Set index
        df.set_index(index_column, drop=False, inplace=True, verify_integrity=True)

        log.write(f"Parsed {len(df)} records from {data_file_name}\n")

        # Import to database
        svc.add_clinical_data(user, df, data_file_name)

        log.write(f"Successfully imported clinical data\n")
        return True, log.getvalue()

    except Exception as e:
        import traceback
        log.write(f"Error: {e}\n")
        log.write(traceback.format_exc())
        return False, log.getvalue()


def process_biospecimen_file(file_path: str, user) -> Tuple[bool, str]:
    """
    Process biospecimen data Excel file and import to database.
    """
    log = StringIO()

    try:
        ext = os.path.splitext(file_path)[1].lower()
        engine = 'xlrd' if ext == '.xls' else 'openpyxl'

        df = pd.read_excel(file_path, engine=engine, keep_default_na=False)
        df.columns = modify_df_column_names(df.columns)

        index_column = 'specimen_id'
        index_names = df[df[index_column] == ''].index
        df.drop(index_names, inplace=True)

        data_file_name = os.path.basename(file_path)
        create_custom_columns(df, set_up_globals.biospecimen_document_name, data_file_name)

        # Don't verify integrity for biospecimen (may have duplicates)
        df.set_index(index_column, drop=False, inplace=True, verify_integrity=False)

        log.write(f"Parsed {len(df)} records from {data_file_name}\n")

        svc.add_biospecimen_data(user, df, data_file_name)

        log.write(f"Successfully imported biospecimen data\n")
        return True, log.getvalue()

    except Exception as e:
        log.write(f"Error: {e}\n")
        return False, log.getvalue()


def parse_assay_metadata(file_path: str) -> Tuple[dict, str]:
    """
    Parse metadata from assay Excel file.

    Returns:
        Tuple of (metadata_dict, error_message or empty string)
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        engine = 'xlrd' if ext == '.xls' else 'openpyxl'

        # Parse metadata sheet
        metadata_df = pd.read_excel(
            file_path,
            sheet_name='Metadata',
            skiprows=range(0, 3),
            engine=engine,
            keep_default_na=False
        )

        metadata_dict = {}
        for _, row in metadata_df.iterrows():
            key = str(row.iloc[0]).strip().lower().replace(' ', '_').replace('-', '_')
            val = str(row.iloc[1]).strip()
            if val and val.lower() != 'nan':
                metadata_dict[key] = val

        return metadata_dict, ""

    except Exception as e:
        return {}, str(e)


def process_assay_file(file_path: str, user, metadata_dict: dict = None) -> Tuple[bool, str]:
    """
    Process assay data Excel file with metadata sheet and import to database.
    """
    log = StringIO()

    try:
        ext = os.path.splitext(file_path)[1].lower()
        engine = 'xlrd' if ext == '.xls' else 'openpyxl'
        data_file_name = os.path.basename(file_path)

        # Parse metadata if not provided
        if metadata_dict is None:
            metadata_dict, error = parse_assay_metadata(file_path)
            if error:
                log.write(f"Error parsing metadata: {error}\n")
                return False, log.getvalue()

        log.write(f"Parsed metadata: {metadata_dict.get('unique_assay_name', 'Unknown')}\n")
        log.write(f"Assay type: {metadata_dict.get('assay_type', 'Unknown')}\n")

        # Validate assay type
        valid_types = [
            set_up_globals.proteomics_document_name,
            set_up_globals.cytokines_document_name,
            set_up_globals.metabolomics_document_name,
            set_up_globals.mirnaseq_document_name,
            set_up_globals.scrnaseq_document_name,
            set_up_globals.seahorse_document_name,
            'BDNF', 'CPET', 'LPS', 'Other'
        ]

        assay_type = metadata_dict.get('assay_type', '')
        if assay_type not in valid_types:
            log.write(f"Error: Invalid assay type: {assay_type}\n")
            log.write(f"Valid types: {', '.join(valid_types)}\n")
            return False, log.getvalue()

        # Parse data sheet
        data_df = pd.read_excel(
            file_path,
            sheet_name='Data Table',
            engine=engine,
            keep_default_na=False
        )

        # Normalize column names
        data_df.columns = modify_df_column_names(data_df.columns)

        # Get sample identifier type
        sample_identifier_type = metadata_dict.get('sample_identifier_type', 'ENID+Timepoint')

        # Create custom columns
        create_custom_columns(data_df, assay_type, data_file_name, index_column=sample_identifier_type)

        log.write(f"Parsed {len(data_df)} data rows\n")

        # Import assay data
        svc.add_assay_meta_data(
            user,
            data_df,
            data_file_name,
            metadata_dict,
            assay_type
        )

        log.write(f"Successfully imported assay data\n")
        return True, log.getvalue()

    except Exception as e:
        log.write(f"Error: {e}\n")
        import traceback
        log.write(traceback.format_exc())
        return False, log.getvalue()
