import mongoengine
from data.gene_symbols import GeneSymbols
from data.ensembl_geneids import EnsemblGeneIDs


class EnsemblTranscriptIDs(mongoengine.Document):
    data_label = mongoengine.StringField(required=True)

    gene_symbol_references = mongoengine.ListField(mongoengine.ReferenceField(GeneSymbols))
    ensembl_geneid_references = mongoengine.ListField(mongoengine.ReferenceField(EnsemblGeneIDs))

    # //--- set up reference lists for each of the other data label types
    # //--- set up reference lists for each pathway ths gene is in

    meta = {
        'db_alias': 'core',
        'collection': 'ensembl_transcriptids'
    }
