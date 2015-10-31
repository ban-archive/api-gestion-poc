import os

import peewee
from playhouse.postgres_ext import PostgresqlExtDatabase

db = PostgresqlExtDatabase(
    os.environ.get('DB_NAME', 'ban'),
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASSWORD'),
    host=os.environ.get('DB_HOST'),
)
test_db = PostgresqlExtDatabase(
    'test_' + os.environ.get('DB_NAME', 'ban'),
    autorollback=True,
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASSWORD'),
    host=os.environ.get('DB_HOST'),
)

# db = peewee.SqliteDatabase(':memory:')
# test_db = peewee.SqliteDatabase('test.sql')
