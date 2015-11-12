import os
import peewee

from playhouse.postgres_ext import PostgresqlExtDatabase

from .fields import *  # noqa

default = PostgresqlExtDatabase(
    os.environ.get('DB_NAME', 'ban'),
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASSWORD'),
    host=os.environ.get('DB_HOST'),
)
test = PostgresqlExtDatabase(
    'test_' + os.environ.get('DB_NAME', 'ban'),
    autorollback=True,
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASSWORD'),
    host=os.environ.get('DB_HOST'),
)


class Model(peewee.Model):

    class Meta:
        database = default
