import datetime
import mongoengine


class User(mongoengine.Document):
    registered_date = mongoengine.DateTimeField(default=datetime.datetime.now)
    name = mongoengine.StringField(required=True)
    email = mongoengine.EmailField(required=True)

    # snake_ids = mongoengine.ListField()
    # cage_ids = mongoengine.ListField()

    meta = {
        'db_alias': 'core',
        'collection': 'users'
    }
