import re

import peewee
from playhouse import postgres_ext, fields
from postgis import Point

__all__ = ['PointField', 'ForeignKeyField', 'CharField', 'IntegerField',
           'HStoreField', 'UUIDField', 'ArrayField', 'DateTimeField',
           'BooleanField', 'BinaryJSONField', 'ZipCodeField',
           'ManyToManyField']


lonlat_pattern = re.compile('^[\[\(]{1}(?P<lon>-?\d{,3}(:?\.\d*)?), ?(?P<lat>-?\d{,3}(\.\d*)?)[\]\)]{1}$')  # noqa


class PointField(peewee.Field):
    db_field = 'point'
    schema_type = 'point'
    srid = 4326

    def db_value(self, value):
        return self.coerce(value)

    def python_value(self, value):
        return self.coerce(value)

    def coerce(self, value):
        if not value:
            return None
        if isinstance(value, Point):
            return value
        if isinstance(value, str):
            search = lonlat_pattern.search(value)
            if search:
                value = (float(search.group('lon')),
                         float(search.group('lat')))
        return Point(value[0], value[1], srid=self.srid)

postgres_ext.PostgresqlExtDatabase.register_fields({'point':
                                                    'geometry(Point)'})


class ForeignKeyField(peewee.ForeignKeyField):

    schema_type = 'integer'

    def coerce(self, value):
        if isinstance(value, peewee.Model):
            value = value.id
        elif isinstance(value, str) and hasattr(self.rel_model, 'coerce'):
            value = self.rel_model.coerce(value).id
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


class IntegerField(peewee.IntegerField):
    schema_type = 'integer'


class HStoreField(postgres_ext.HStoreField):
    schema_type = 'dict'


class BinaryJSONField(postgres_ext.BinaryJSONField):
    schema_type = 'dict'


class UUIDField(peewee.UUIDField):
    pass


class ArrayField(postgres_ext.ArrayField):
    schema_type = 'list'


class DateTimeField(peewee.DateTimeField):
    pass


class BooleanField(peewee.BooleanField):
    schema_type = 'bool'


class ZipCodeField(CharField):

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 5
        kwargs['unique'] = True
        super().__init__(*args, **kwargs)

    def coerce(self, value):
        value = str(value)
        if not len(value) == 5 or not value.isdigit():
            raise ValueError('Invalid zipcode')
        return value


class ManyToManyField(fields.ManyToManyField):
    schema_type = 'list'
