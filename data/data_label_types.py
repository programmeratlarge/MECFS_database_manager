import mongoengine
import set_up_globals

data_label_type_choices = set_up_globals.data_label_type_choices


class DataLabels(mongoengine.Document):
    data_label_type = mongoengine.StringField(required=True, choices=data_label_type_choices)
    data_label = mongoengine.StringField(required=True)
    data_label_name = mongoengine.StringField()

    gene_symbol_references = mongoengine.ListField(mongoengine.ReferenceField('self'))
    ensembl_geneid_references = mongoengine.ListField(mongoengine.ReferenceField('self'))
    cytokine_label_references = mongoengine.ListField(mongoengine.ReferenceField('self'))
    metabolomic_label_references = mongoengine.ListField(mongoengine.ReferenceField('self'))

    meta = {
        'db_alias': 'core',
        'collection': 'data_labels',
        'ordering': ['-data_label'],
        'indexes': ['data_label']
    }


class DataLabelPathways(mongoengine.Document):
    pathway_name = mongoengine.StringField(required=True)
    description = mongoengine.StringField()
    data_label_type = mongoengine.StringField(required=True, choices=data_label_type_choices)
    data_label_references = mongoengine.ListField(mongoengine.ReferenceField(DataLabels))

    meta = {
        'db_alias': 'core',
        'collection': 'data_label_pathways',
        'ordering': ['-pathway_name'],
        'indexes': ['pathway_name']
    }


# class EnsemblTranscriptIDs(mongoengine.Document):
#     data_label = mongoengine.StringField(required=True)
#
#     meta = {
#         'db_alias': 'core',
#         'collection': 'ensembl_transcriptids',
#         'ordering': ['-data_label'],
#         'indexes': ['data_label']
#     }


# class EnsemblGeneIDs(mongoengine.Document):
#     data_label = mongoengine.StringField(required=True)
#
#     meta = {
#         'db_alias': 'core',
#         'collection': 'ensembl_geneids',
#         'ordering': ['-data_label'],
#         'indexes': ['data_label']
#     }


# class GeneSymbols(mongoengine.Document):
#     data_label = mongoengine.StringField(required=True)
#
#     meta = {
#         'db_alias': 'core',
#         'collection': 'gene_symbols',
#         'ordering': ['-data_label'],
#         'indexes': ['data_label']
#     }


# class CytokineLabels(mongoengine.Document):
#     data_label = mongoengine.StringField(required=True)
#
#     meta = {
#         'db_alias': 'core',
#         'collection': 'cytokine_labels',
#         'ordering': ['-data_label'],
#         'indexes': ['data_label']
#     }


# Now that all classes have been defined, set up each of the reference lists:
# Each data label type should have references to every other data label type,
# allowing us to set up many-to-many relationships between each data label type
# class GeneSymbolsToEnsemblGeneIDs(mongoengine.Document):
#     gene_symbol_data_label = mongoengine.StringField()
#     ensembl_geneid_data_label = mongoengine.StringField()
#     gene_symbol_reference = mongoengine.ReferenceField(GeneSymbols)
#     ensembl_geneid_reference = mongoengine.ReferenceField(EnsemblGeneIDs)
#
#     meta = {
#         'db_alias': 'core',
#         'collection': 'gene_symbols_to_ensembl_gene_ids',
#         'ordering': ['-gene_symbol_data_label'],
#         'indexes': ['gene_symbol_data_label', 'ensembl_geneid_data_label']
#     }


# class GeneSymbolsToCytokineLabels(mongoengine.Document):
#     gene_symbol_data_label = mongoengine.StringField()
#     cytokine_data_label = mongoengine.StringField()
#     gene_symbol_reference = mongoengine.ReferenceField(GeneSymbols)
#     cytokine_label_reference = mongoengine.ReferenceField(CytokineLabels)
#
#     meta = {
#         'db_alias': 'core',
#         'collection': 'gene_symbols_to_cytokine_labels',
#         'ordering': ['-gene_symbol_data_label'],
#         'indexes': ['gene_symbol_data_label', 'cytokine_data_label']
#     }
