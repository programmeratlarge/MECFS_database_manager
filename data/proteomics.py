import datetime
import mongoengine
from data.biospecimens import Biospecimen
from data.users import User
from data.assay_results import AssayResults


# time_choices = ('t1', 't2', 't3')
# cpet_day_choice = ('D1', 'D2')
# pre_post_cpet_choice = ('PRE', 'POST')
timepoint_choices = ('D1-PRE', 'D1-POST', 'D2-PRE', 'D2-POST')


class Proteomic(mongoengine.EmbeddedDocument):
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)
    last_modified_by = mongoengine.ReferenceField(User, required=True)
    last_modified_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    unique_id = mongoengine.StringField(required=True)
    analysisid = mongoengine.IntField()
    data_file_name = mongoengine.StringField(required=True)
    biospecimen_data_reference = mongoengine.ReferenceField(Biospecimen)
    timepoint = mongoengine.StringField(required=True, choices=timepoint_choices)
    annot_1 = mongoengine.StringField()
    annot_2 = mongoengine.StringField()
    annot_3 = mongoengine.StringField()

    # Add metadata from upload form
    submitter_name = mongoengine.StringField()
    submitter_netid = mongoengine.StringField()
    pi_name = mongoengine.StringField()
    assay_type = mongoengine.StringField()
    assay_method = mongoengine.StringField()
    biospecimen_type = mongoengine.StringField()
    dataset_name = mongoengine.StringField()
    dataset_annotation = mongoengine.StringField()
    data_label_type = mongoengine.StringField()
    comment = mongoengine.StringField()
    units = mongoengine.StringField()
    normalization_method = mongoengine.StringField()
    pipeline = mongoengine.StringField()

    assay_results = mongoengine.EmbeddedDocumentListField(AssayResults)

    # time = mongoengine.StringField(required=True, choices=time_choices)
    # cpet_day = mongoengine.StringField(choices=cpet_day_choice)
    # pre_post_cpet = mongoengine.StringField(choices=pre_post_cpet_choice)
    # run = mongoengine.StringField(required=True)
