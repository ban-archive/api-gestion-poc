import os

import peewee
from playhouse.postgres_ext import PostgresqlExtDatabase


class DBProxy(peewee.Proxy):

    prefix = ''

    def __getattr__(self, attr):
        if not self.obj:
            db = PostgresqlExtDatabase(
                self.prefix + os.environ.get('DB_NAME', 'ban'),
                user=os.environ.get('DB_USER'),
                password=os.environ.get('DB_PASSWORD'),
                host=os.environ.get('DB_HOST'),
                port=os.environ.get('DB_PORT'),
            )
            self.initialize(db)
        return getattr(self.obj, attr)


class TestDBProxy(DBProxy):

    prefix = 'test_'

default = DBProxy()
test = TestDBProxy()

# test = PostgresqlExtDatabase(
#     'test_' + os.environ.get('DB_NAME', 'ban'),
#     autorollback=True,
#     user=os.environ.get('DB_USER'),
#     password=os.environ.get('DB_PASSWORD'),
#     host=os.environ.get('DB_HOST'),
#     port=os.environ.get('DB_PORT'),
# )
