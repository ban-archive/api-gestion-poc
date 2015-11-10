import re

import peewee
from playhouse.postgres_ext import HStoreField

lonlat_pattern = re.compile('^[\[\(]{1}(?P<lon>-?\d{,3}(:?\.\d*)?), ?(?P<lat>-?\d{,3}(\.\d*)?)[\]\)]{1}$')  # noqa
point_template = 'POINT ({} {})'

# https://github.com/MAPC/rental-listing-aggregator/blob/09d3d8d75ea3697431dd080f49c4fc1f28a83263/.ipynb_checkpoints/Untitled-checkpoint.ipynb
# https://github.com/mima3/estat/blob/537689ad4ebc96af34e1c66a9997241fa847d8c1/estat_db.py
# https://github.com/ryanj/flask-postGIS/blob/master/map.py
# http://chrishaganreporting.com/2014/03/inserting-geometry-with-postgis-and-psycopg2/
# http://stackoverflow.com/questions/14940285/using-postgis-on-python-3
# http://stackoverflow.com/questions/29888040/how-to-join-on-spatial-functions-in-peewee


class PointField(peewee.Field):
    db_field = 'point'
    schema_type = 'point'

    def db_value(self, value):
        return str(self.coerce(value))

    def python_value(self, value):
        return self.coerce(value)

    def coerce(self, value):
        if not value:
            value = tuple()
        elif isinstance(value, str):
            search = lonlat_pattern.search(value)
            if search:
                value = (float(search.group('lon')),
                         float(search.group('lat')))
        elif isinstance(value, list):
            value = tuple(value)
        return value


class ForeignKeyField(peewee.ForeignKeyField):

    schema_type = 'integer'

    def coerce(self, value):
        if isinstance(value, peewee.Model):
            value = value.id
        return super().coerce(value)


class CharField(peewee.CharField):
    schema_type = 'string'

    def __init__(self, *args, **kwargs):
        if 'default' not in kwargs:
            kwargs['default'] = ''
        super().__init__(*args, **kwargs)

    def coerce(self, value):
        if value is None:
            value = ''
        return super().coerce(value)

    def python_value(self, value):
        value = self.coerce(value)
        return super().python_value(value)

peewee.PostgresqlDatabase.register_fields({'point': 'point'})
peewee.SqliteDatabase.register_fields({'point': 'point'})


class IntegerField(peewee.IntegerField):
    schema_type = 'integer'


class HStoreField(HStoreField):
    schema_type = 'dict'
