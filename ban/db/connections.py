import peewee
from playhouse.postgres_ext import PostgresqlExtDatabase
from ban.core import config
import postgis


class DBProxy(peewee.Proxy):

    prefix = ''

    def __getattr__(self, attr):
        if not self.obj:
            db = PostgresqlExtDatabase(
                self.prefix + config.DB_NAME,
                user=config.get('DB_USER'),
                password=config.get('DB_PASSWORD'),
                host=config.get('DB_HOST'),
                port=config.get('DB_PORT'),
            )
            self.initialize(db)
            postgis.register(self.obj.get_cursor())
        return getattr(self.obj, attr)


class TestDBProxy(DBProxy):

    prefix = 'test_'

default = DBProxy()
test = TestDBProxy()
