import datetime
import mongoengine
from data.users import User


class Redcap(mongoengine.EmbeddedDocument):
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)
    last_modified_by = mongoengine.ReferenceField(User, required=True)
    last_modified_date = mongoengine.DateTimeField(default=datetime.datetime.now)

    data_file_name = mongoengine.StringField(required=True)
    redcap_event_name = mongoengine.StringField()
    redcap_data_access_group = mongoengine.StringField()
    ccc_enid = mongoengine.IntField()
    ccc_date = mongoengine.DateTimeField(required=True)
    ccc_fatigue___1 = mongoengine.StringField()
    ccc_fatigue___2 = mongoengine.StringField()
    ccc_pem___1 = mongoengine.StringField()
    ccc_pem___2 = mongoengine.StringField()
    ccc_pem___3 = mongoengine.StringField()
    ccc_pem___4 = mongoengine.StringField()
    ccc_pem___5 = mongoengine.StringField()
    ccc_sleep___1 = mongoengine.StringField()
    ccc_sleep___2 = mongoengine.StringField()
    ccc_sleep___3 = mongoengine.StringField()
    # //---
