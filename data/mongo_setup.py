import os
import mongoengine


def global_init(database_name: str, host: str = None):
    """
    Initialize MongoDB connection.

    Args:
        database_name: Name of the database to connect to
        host: MongoDB host. If None, uses MONGO_HOST env var or defaults to localhost
    """
    if host is None:
        host = os.environ.get('MONGO_HOST', 'localhost')

    port = int(os.environ.get('MONGO_PORT', '27017'))

    mongoengine.register_connection(
        alias='core',
        name=database_name,
        host=host,
        port=port
    )
