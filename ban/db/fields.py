import json
import re

import peewee

from playhouse import postgres_ext, fields
from playhouse.fields import PasswordField as PWDField
from postgis import Point

__all__ = ['PointField', 'ForeignKeyField', 'CharField', 'IntegerField',
           'HStoreField', 'UUIDField', 'ArrayField', 'DateTimeField',
           'BooleanField', 'BinaryJSONField', 'PostCodeField',
           'ManyToManyField', 'PasswordField', 'ProxiesField', 'ProxyField']


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


class DateTimeField(peewee.DateTimeField):
    pass


class BooleanField(peewee.BooleanField):
    schema_type = 'bool'


class PostCodeField(CharField):

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 5
        super().__init__(*args, **kwargs)

    def coerce(self, value):
        value = str(value)
        if not len(value) == 5 or not value.isdigit():
            raise ValueError('Invalid postcode')
        return value


class ResourceListQueryResultWrapper(peewee.ModelQueryResultWrapper):

    def process_row(self, row):
        instance = super().process_row(row)
        return instance.as_list


class ManyToManyQuery(fields.ManyToManyQuery):

    def _get_result_wrapper(self):
        return getattr(self, '_result_wrapper', None) or ProxiesResultWrapper

    @peewee.returns_clone
    def as_resource_list(self):
        self._result_wrapper = ResourceListQueryResultWrapper


class ManyToManyField(fields.ManyToManyField):
    schema_type = 'list'

    def __init__(self, *args, **kwargs):
        # Try to better conform to Field API.
        self.null = True
        self.unique = False
        self.index = False
        super().__init__(*args, **kwargs)

    def coerce(self, value):
        if not isinstance(value, (tuple, list, peewee.SelectQuery)):
            value = [value]
        # https://github.com/coleifer/peewee/pull/795
        value = [self.rel_model.get(self.rel_model.id == item)
                 if not isinstance(item, self.rel_model)
                 else item
                 for item in value]
        return super().coerce(value)

    def add_to_class(self, model_class, name):
        # https://github.com/coleifer/peewee/issues/794
        model_class._meta.fields[name] = self
        super().add_to_class(model_class, name)


class ProxiesResultWrapper(peewee.ModelQueryResultWrapper):

    def process_row(self, row):
        instance = super().process_row(row)
        # TODO find a way to make the relation asymetric
        return getattr(instance, 'real', instance)


class ProxiesQuery(ManyToManyQuery):

    def add(self, value, clear_existing=False):
        if not isinstance(value, (list, tuple, peewee.SelectQuery)):
            value = [value]
        value = [item.proxy for item in value]
        super().add(value, clear_existing)

    def remove(self, value):
        if not isinstance(value, (list, tuple)):
            value = [value]
        value = [item.proxy for item in value]
        super().remove(value)


class ProxiesFieldDescriptor(fields.ManyToManyFieldDescriptor):

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            # See https://github.com/coleifer/peewee/issues/838
            return (ProxiesQuery(instance, self, self.rel_model)
                    .select()
                    .join(self.through_model)
                    .join(self.model_class)
                    .where(self.src_fk == instance))
        return self.field


class ProxiesField(ManyToManyField):

    def _get_descriptor(self):
        return ProxiesFieldDescriptor(self)

    def coerce_one(self, value):
        if isinstance(value, int):
            value = self.rel_model.get(self.rel_model.id == value)
        if isinstance(value, self.rel_model):
            value = value.real
        return value

    def coerce(self, value):
        if not isinstance(value, (tuple, list, peewee.SelectQuery)):
            value = [value]
        return [self.coerce_one(item) for item in value]


class ProxyRelationDescriptor(peewee.RelationDescriptor):

    def __get__(self, instance, instance_type=None):
        value = super().__get__(instance, instance_type)
        if instance is not None:
            return value.real
        return value

    def __set__(self, instance, value):
        if (isinstance(value, peewee.Model)
                and not isinstance(value, self.rel_model)):
            value = value.proxy
        super().__set__(instance, value)


class ProxyField(ForeignKeyField):

    def _get_descriptor(self):
        return ProxyRelationDescriptor(self, self.rel_model)

    def coerce(self, value):
        if not isinstance(value, (int, str)):
            if not isinstance(value, self.rel_model):
                value = value.proxy
            value = value._get_pk_value()
        else:
            value = int(value)
        return value

    def db_value(self, value):
        value = self.coerce(value)
        return super().db_value(value)

    def python_value(self, value):
        value = super().python_value(value)
        return value.real


class PasswordField(PWDField):

    def python_value(self, value):
        if value is None:
            return value
        return super().python_value(value)
