import mongoengine
from data.ensembl_geneids import EnsemblGeneIDs
from data.ensembl_transcriptids import EnsemblTranscriptIDs


class GeneSymbols(mongoengine.Document):
    data_label = mongoengine.StringField(required=True)
    ensembl_geneid_references = mongoengine.ListField(mongoengine.ReferenceField(EnsemblGeneIDs))
    ensembl_transcriptid_references = mongoengine.ListField(mongoengine.ReferenceField(EnsemblTranscriptIDs))

    # //--- set up reference lists for each of the other data label types
    # //--- set up reference lists for each pathway ths gene is in

    meta = {
        'db_alias': 'core',
        'collection': 'gene_symbols'
    }
