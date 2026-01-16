import datetime
import mongoengine

from data.users import User
from data.biospecimens import Biospecimen


class ScRNAseqSummary(mongoengine.EmbeddedDocument):
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)
    last_modified_by = mongoengine.ReferenceField(User, required=True)
    last_modified_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    # excel_file_id = mongoengine.IntField(required=True, primary_key=True)
    data_file_name = mongoengine.StringField(required=True)
    sampleid = mongoengine.IntField(required=True, primary_key=True)
    biospecimen_data_reference = mongoengine.ReferenceField(Biospecimen)
    estimated_number_of_cells = mongoengine.IntField(required=True)
    mean_reads_per_cell = mongoengine.IntField(required=True)
    median_genes_per_cell = mongoengine.IntField(required=True)
    number_of_reads = mongoengine.IntField(required=True)
    valid_barcodes = mongoengine.FloatField()
    sequencing_saturation = mongoengine.FloatField()
    q30_bases_in_barcode = mongoengine.FloatField()
    q30_bases_in_rna_read = mongoengine.FloatField()
    q30_bases_in_sample_index = mongoengine.FloatField()
    q30_bases_in_umi = mongoengine.FloatField()
    reads_mapped_to_genome = mongoengine.FloatField()
    reads_mapped_confidently_to_genome = mongoengine.FloatField()
    reads_mapped_confidently_to_intergenic_regions = mongoengine.FloatField()
    reads_mapped_confidently_to_intronic_regions = mongoengine.FloatField()
    reads_mapped_confidently_to_exonic_regions = mongoengine.FloatField()
    reads_mapped_confidently_to_transcriptome = mongoengine.FloatField()
    reads_mapped_antisense_to_gene = mongoengine.FloatField()
    fraction_reads_in_cells = mongoengine.FloatField()
    total_genes_detected = mongoengine.FloatField()
    median_umi_counts_per_cell = mongoengine.FloatField()
    ten_x_batch = mongoengine.IntField()
    firstpass_nextseq = mongoengine.IntField()
    secondpass_nextseq = mongoengine.IntField()
    hiseq_x5 = mongoengine.IntField()
    novaseq_s4 = mongoengine.IntField()
    nextseq2k = mongoengine.IntField()
    brc_id = mongoengine.StringField()
    enid = mongoengine.IntField()
    sample_name = mongoengine.StringField()
    bc = mongoengine.StringField()
    notes = mongoengine.StringField()

    # @property
    # def target(self):
    #     # dt = datetime.datetime.now() - self.date_received
    #     return 0
