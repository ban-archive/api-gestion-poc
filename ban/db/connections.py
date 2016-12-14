from playhouse.postgres_ext import PostgresqlExtDatabase
from ban.core import config
import postgis


class DB(PostgresqlExtDatabase):

    prefix = ''
    postgis_registered = False

    def __init__(self):
        super().__init__(None, autorollback=True)

    def connect(self):
        # Deal with connection kwargs at connect time only, because we want
        # to be able to instantiate the db object bedore patching the
        # connection kwargs: peewee instanciate it at python parse time, while
        # we want to set connection kwargs after parsing command line.
        self.init(
            self.prefix + config.DB_NAME,
            user=config.get('DB_USER'),
            password=config.get('DB_PASSWORD'),
            host=config.get('DB_HOST'),
            port=config.get('DB_PORT')
        )
        super().connect()

    def initialize_connection(self, conn):
        if not self.postgis_registered:
            postgis.register(conn.cursor())
            self.postgis_registered = True


database = DB()
