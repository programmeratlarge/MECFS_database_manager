#

# Version history:

# ME/CFS version 1 (MECFS_V1) - original version:

# Set up globals
MECFSVersion = 'MECFS_V1'
MECFS_data_upload_file_version = '0.3'
# data_folder = '/workdir/data/'
# data_folder = 'C:/Users/prm88/Documents/Box/genome_innovation_hub/mecfs_code/data/'
data_folder = '../data/'
database_name = 'mecfs_db_consolidated_assays'
# database_name = 'mecfs_db_test_redcap'
# database_name = 'mecfs_db_demo'
testMode = True

users = [('Paul Munn', 'prm88@cornell.edu'),
         ('Faraz Ahmed', 'fa286@cornell.edu'),
         ('Jen Grenier', 'jgrenier@cornell.edu'),
         ('Carl Franconi', 'carl.franconi@cornell.edu'),
         ('Ludovic Giloteaux', 'lg349@cornell.edu'),
         ('Arnaud Didier Germain', 'ag297@cornell.edu'),
         ('Katie Glass', 'kg432@cornell.edu')
         ]

exitResponseList = ['x', 'bye', 'exit', 'exit()', 'quit', 'q', 'q()']

import_log_file = 'data_import.log'

enid_document_name = 'demographic ENIDs'
clinical_document_name = 'demographic'
biospecimen_document_name = 'biospecimens'
proteomics_document_name = 'Proteomics'
cytokines_document_name = 'Cytokines'
metabolomics_document_name = 'Metabolomics'
scrnaseq_summary_document_name = 'scRNA-seq summary'
scrnaseq_document_name = 'scRNAseq'
mirnaseq_document_name = 'miRNA'
data_label_type_document_name = 'data label type'
data_label_pathway_document_name = 'data label pathway'
seahorse_document_name = 'Flux and flow cytometry assays'
cpet_recovery_document_name = 'Survey'
ev_pilot_study_document_name = 'Cytokines'

gene_symbol_data_label_type = 'Gene Symbol'
ensembl_gene_id_data_label_type = 'Ensembl Gene ID'
cytokine_data_label_type = 'Cytokine Label'
metabolomics_data_label_type = 'Compound ID'

# //--- replace hardcoding with global reference
data_label_type_choices = (gene_symbol_data_label_type,
                           ensembl_gene_id_data_label_type,
                           cytokine_data_label_type,
                           metabolomics_data_label_type,
                           'Other')
# 'NCBI GeneID',
# 'NCBI RefSeq ID',
# 'Ensembl TranscriptID',
data_label_type_list = [val for val in data_label_type_choices]

gene_symbol_to_ensembl_geneid_ref = 'Gene Symbol to Ensembl Gene ID'
gene_symbol_to_cytokine_label_ref = 'Gene Symbol to Cytokine Label'

summary_type_choices = ('Average', 'GSEA')

binnedColumnsDict = {'age': [(18, 35), (35, 45), (45, 55), (55, 70)],
                     # 'bmi': [(0, 25), (25, 27), (27, 30), (30, 100)],
                     # 'bmi': [(0, 18.5), (18.5, 25), (25, 30), (30, 35), (35, 100)],
                     'bmi': [(0, 18.5), (18.5, 25), (25, 27), (27, 30), (30, 100)],
                     'mecfs_duration': [(0, 5), (5, 100)],
                     'pf': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'rp': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'bp': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'gh': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'vt': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'sf': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     're': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'mh': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'pf_nbs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'rp_nbs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'bp_nbs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'gh_nbs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'vt_nbs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'sf_nbs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     're_nbs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'mh_nbs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'pcs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'mcs': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'mfi20_gf': [(0, 5), (5, 10), (10, 15), (15, 20)],
                     'mfi20_pf': [(0, 5), (5, 10), (10, 15), (15, 20)],
                     'mfi20_ra': [(0, 5), (5, 10), (10, 15), (15, 20)],
                     'mfi20_rm': [(0, 5), (5, 10), (10, 15), (15, 20)],
                     'mfi20_mf': [(0, 5), (5, 10), (10, 15), (15, 20)],
                     'mfi20_total': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'bas_score': [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)],
                     'pem_max_delta': [(0, 2), (2, 10)]}

exportDemographicColumnsForRTIMinimum = ['cor_id', 'phenotype', 'biospecimen_type',
                                         'sample_identifier_type', 'annot_1', 'annot_2', 'annot_3']

exportDemographicColumnsForRTIKeller = ['cor_id', 'phenotype', 'biospecimen_type',
                                        'sample_identifier_type', 'annot_1', 'annot_2', 'annot_3',
                                        'site', 'sex', 'race', 'age', 'age_binned', 'height_in', 'weight_lb',
                                        'bmi', 'bmi_binned', 'bas_score', 'q_education', 'q_reclined',
                                        'q_sleeprefreshing', 'q_hoursinbed']

exportDemographicColumnsForRTIFull = ['study_id', 'cor_id', 'pub_id', 'site', 'sex', 'phenotype', 'race',
               'age', 'age_binned', 'height_in', 'weight_lb', 'bmi', 'bmi_binned', 'mecfs_sudden_gradual',
               'PF', 'RP', 'BP', 'GH', 'VT', 'SF', 'RE', 'MH', 'PF_NBS', 'RP_NBS', 'BP_NBS',
               'GH_NBS', 'VT_NBS', 'SF_NBS', 'RE_NBS', 'MH_NBS', 'PCS', 'MCS', 'bas_score',
               'mfi20_gf', 'mfi20_pf', 'mfi20_ra', 'mfi20_rm', 'mfi20_mf', 'mfi20_total',
               'q_oisymptoms', 'q_gisymptoms', 'q_probiotics', 'q_education', 'q_reclined', 'q_sleeprefreshing', 'q_hoursinbed']

exportAssayColumnsForRTI = ['cor_id', 'timepoint', 'sample_identifier_type', 'annot_1', 'annot_2', 'annot_3']

# PF, RP, BP, GH, VT, SF, RE, MH, PCS, and MCS are the 10 subscales of the SF-36v2 Health Survey
exportDemographicColumnsForSCpaper = ['study_id', 'cor_id', 'sex', 'phenotype', 'age', 'bmi', 'mecfs_sudden_gradual',
                                      'mecfs_duration', 'GH', 'PCS', 'mfi20_total', 'pem_max_delta']

print('ME/CFS version:', MECFSVersion)
print('Data folder:', data_folder)
print('Database name:', database_name)
