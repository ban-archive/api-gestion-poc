from datetime import timezone
import json
import re

import peewee

from playhouse import postgres_ext, fields
from playhouse.fields import PasswordField as PWDField
from postgis import Point
from psycopg2.extras import DateTimeTZRange

__all__ = ['PointField', 'ForeignKeyField', 'CharField', 'IntegerField',
           'HStoreField', 'UUIDField', 'ArrayField', 'DateTimeField',
           'BooleanField', 'BinaryJSONField', 'PostCodeField', 'FantoirField',
           'ManyToManyField', 'PasswordField', 'DateRangeField', 'TextField']


lonlat_pattern = re.compile('^[\[\(]{1}(?P<lon>-?\d{,3}(:?\.\d*)?), ?(?P<lat>-?\d{,3}(\.\d*)?)[\]\)]{1}$')  # noqa


peewee.OP.update(
    BBOX2D='&&',
    BBOXCONTAINS='~',
    BBOXCONTAINED='@',
)
postgres_ext.PostgresqlExtDatabase.register_ops({
    peewee.OP.BBOX2D: peewee.OP.BBOX2D,
    peewee.OP.BBOXCONTAINS: peewee.OP.BBOXCONTAINS,
    peewee.OP.BBOXCONTAINED: peewee.OP.BBOXCONTAINED,
})


# TODO: mv to a third-party module.
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
        if isinstance(value, dict):  # GeoJSON
            value = value['coordinates']
        if isinstance(value, str):
            search = lonlat_pattern.search(value)
            if search:
                value = (float(search.group('lon')),
                         float(search.group('lat')))
        return Point(value[0], value[1], srid=self.srid)

    def contained(self, geom):
        return peewee.Expression(self, peewee.OP.BBOXCONTAINED, geom)

    def contains(self, geom):
        return peewee.Expression(self, peewee.OP.BBOXCONTAINS, geom)

    def in_bbox(self, south, north, east, west):
        return self.contained(
            peewee.fn.ST_MakeBox2D(Point(west, south, srid=self.srid),
                                   Point(east, north, srid=self.srid)),
            )


postgres_ext.PostgresqlExtDatabase.register_fields({'point':
                                                    'geometry(Point)'})


class DateRangeField(peewee.Field):
    db_field = 'tstzrange'
    schema_type = 'tstzrange'

    def db_value(self, value):
        return self.coerce(value)

    def python_value(self, value):
        return self.coerce(value)

    def coerce(self, value):
        if not value:
            value = [None, None]
        if isinstance(value, (list, tuple)):
            # '[)' means include lower bound but not upper.
            value = DateTimeTZRange(*value, bounds='[)')
        return value

    def contains(self, dt):
        return peewee.Expression(self, peewee.OP.ACONTAINS, dt)


class ForeignKeyField(peewee.ForeignKeyField):

    schema_type = 'foreignkey'

    def coerce(self, value):
        if not value:
            return None
        if isinstance(value, peewee.Model):
            value = value.pk
        elif isinstance(value, dict):
            # We have a resource dict.
            value = value['id']
        if isinstance(value, str) and hasattr(self.rel_model, 'coerce'):
            value = self.rel_model.coerce(value).pk
        return super().coerce(value)

    def _get_related_name(self):
        # cf https://github.com/coleifer/peewee/pull/844
        return (self._related_name or '{classname}_set').format(
                                        classname=self.model_class._meta.name)


class CharField(peewee.CharField):
    schema_type = 'string'

    def coerce(self, value):
        if self.null and not value:
            return None
        return super().coerce(value)


class TextField(peewee.TextField):
    schema_type = 'string'

    def coerce(self, value):
        if self.null and not value:
            return None
        return super().coerce(value)


class IntegerField(peewee.IntegerField):
    schema_type = 'integer'


class HStoreField(postgres_ext.HStoreField):
    schema_type = 'dict'

    def coerce(self, value):
        if isinstance(value, str):
            value = json.loads(value)
        return super().coerce(value)


class BinaryJSONField(postgres_ext.BinaryJSONField):
    schema_type = 'dict'


class UUIDField(peewee.UUIDField):
    pass


class ArrayField(postgres_ext.ArrayField):
    schema_type = 'list'

    def coerce(self, value):
        if value and not isinstance(value, (list, tuple)):
            value = [value]
        return value


class DateTimeField(postgres_ext.DateTimeTZField):
    schema_type = 'datetime'

    def python_value(self, value):
        value = super().python_value(value)
        if value:
            # PSQL store dates in the server timezone, but we only want to
            # deal with UTC ones.
            return value.astimezone(timezone.utc)


class BooleanField(peewee.BooleanField):
    schema_type = 'bool'


class PostCodeField(CharField):

    max_length = 5

    def coerce(self, value):
        value = str(value)
        if not len(value) == 5 or not value.isdigit():
            raise ValueError('Invalid postcode "{}"'.format(value))
        return value


class FantoirField(CharField):

    max_length = 9

    def coerce(self, value):
        if not value:
            return None
        value = str(value)
        if len(value) == 10:
            value = value[:9]
        if not len(value) == 9:
            raise ValueError('FANTOIR must be municipality INSEE '
                             '+ 4 first chars of FANTOIR "{}"'.format(value))
        return value


class ResourceListQueryResultWrapper(peewee.ModelQueryResultWrapper):

    def process_row(self, row):
        instance = super().process_row(row)
        return instance.as_relation


class ManyToManyQuery(fields.ManyToManyQuery):

    def _get_result_wrapper(self):
        return (getattr(self, '_result_wrapper', None) or
                ResourceListQueryResultWrapper)

    @peewee.returns_clone
    def as_resource_list(self):
        self._result_wrapper = ResourceListQueryResultWrapper


class ManyToManyField(fields.ManyToManyField):
    schema_type = 'list'

    def __init__(self, *args, **kwargs):
        # ManyToManyField is not a real "Field", so try to better conform to
        # Field API.
        # https://github.com/coleifer/peewee/issues/794
        self.null = True
        self.unique = False
        self.index = False
        super().__init__(*args, **kwargs)

    def coerce(self, value):
        if not isinstance(value, (tuple, list, peewee.SelectQuery)):
            value = [value]
        # https://github.com/coleifer/peewee/pull/795
        value = [self.rel_model.coerce(item)
                 if not isinstance(item, self.rel_model)
                 else item
                 for item in value]
        return super().coerce(value)

    def add_to_class(self, model_class, name):
        # https://github.com/coleifer/peewee/issues/794
        model_class._meta.fields[name] = self
        super().add_to_class(model_class, name)


class PasswordField(PWDField):

    def python_value(self, value):
        if value is None:
            return value
        return super().python_value(value)
