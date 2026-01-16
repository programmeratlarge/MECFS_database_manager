import datetime
import mongoengine
# from mongoengine.queryset.visitor import Q
from data.users import User

event_type_choice = ('Import',
                     'Query',
                     'Login'
                     'Logout')


class Event_log(mongoengine.Document):
    created_by = mongoengine.ReferenceField(User, required=True)
    created_date = mongoengine.DateTimeField(required=True)

    event_type = mongoengine.StringField(required=True, choices=event_type_choice)
    exception_type = mongoengine.StringField()
    success = mongoengine.BooleanField(required=True)
    file_name = mongoengine.StringField()
    message = mongoengine.StringField()
    study_id = mongoengine.IntField()
    sample_id = mongoengine.IntField()
    document_id = mongoengine.StringField()
    sub_document_id = mongoengine.StringField()
    comment = mongoengine.StringField()

    @mongoengine.queryset_manager
    def find_failures(doc_cls, queryset):
        return queryset.filter(success=False).order_by('-created_date')

    # @property
    # def days_since_received(self):
    #     dt = datetime.datetime.now() - self.date_received
    #     return dt.days
    meta = {
        'db_alias': 'core',
        'collection': 'event_log'
        # 'indexes': ['study_id', 'site', '$phenotype']
    }
