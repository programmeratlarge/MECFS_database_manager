import mongoengine
from data.gene_symbols import GeneSymbols
from data.ensembl_transcriptids import EnsemblTranscriptIDs


class EnsemblGeneIDs(mongoengine.Document):
    data_label = mongoengine.StringField(required=True)
    gene_symbol_references = mongoengine.ListField(mongoengine.ReferenceField(GeneSymbols))
    ensembl_transcriptid_references = mongoengine.ListField(mongoengine.ReferenceField(EnsemblTranscriptIDs))

    meta = {
        'db_alias': 'core',
        'collection': 'ensembl_geneids'
    }
