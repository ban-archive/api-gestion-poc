from datetime import datetime, timezone
import json
import re

import peewee

from playhouse import postgres_ext, fields
from postgis import Point
from psycopg2.extras import DateTimeTZRange

from ban.core.exceptions import ValidationError, IsDeletedError
from . import cache

__all__ = ['PointField', 'ForeignKeyField', 'CharField', 'IntegerField',
           'HStoreField', 'UUIDField', 'ArrayField', 'DateTimeField',
           'BooleanField', 'BinaryJSONField', 'FantoirField',
           'ManyToManyField', 'DateRangeField', 'TextField',
           'CachedForeignKeyField', 'NameField']


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
class PointField(peewee.Field, postgres_ext.IndexedFieldMixin):
    db_field = 'point'
    __data_type__ = Point
    # TODO how to deal properly with custom type?
    # Or should we just accept geojson (and not [lat, lon]…)?
    __schema_type__ = 'object'
    __schema_format__ = 'geojson'
    srid = 4326
    index_type = 'GiST'

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
            else:
                if not value[0].isdigit() or not value[1].isdigit():
                    raise ValueError
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
    __data_type__ = datetime
    __schema_type__ = 'string'
    __schema_format__ = 'date-time'

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


class CachedRelationDescriptor(peewee.RelationDescriptor):

    def get_object_or_id(self, instance):
        rel_id = instance._data.get(self.att_name)
        if not rel_id:
            return rel_id
        keys = (self.rel_model.__name__, rel_id)
        return cache.cache(keys, super().get_object_or_id, instance)


class ForeignKeyField(peewee.ForeignKeyField):

    __data_type__ = int
    __schema_type__ = 'integer'

    def coerce(self, value, deleted=True, level1=0):
        if not value:
            return None
        if isinstance(value, dict):
            # We have a resource dict.
            value = value['id']
        if hasattr(self.rel_model, 'coerce'):
            value = self.rel_model.coerce(value, None, level1)
        if isinstance(value, peewee.Model):
            if deleted is False and value.deleted_at:
                raise IsDeletedError(value)
            value = value.pk
        return super().coerce(value)

    def _get_related_name(self):
        # cf https://github.com/coleifer/peewee/pull/844
        return (self._related_name or '{classname}_set').format(
                                        classname=self.model_class._meta.name)


class CachedForeignKeyField(ForeignKeyField):

    def _get_descriptor(self):
        return CachedRelationDescriptor(self, self.rel_model)


class CharField(peewee.CharField):
    __data_type__ = str
    __schema_type__ = 'string'

    def __init__(self, *args, **kwargs):
        if 'format' in kwargs:
            self.regex = re.compile(kwargs.pop('format'))
        if 'length' in kwargs:
            kwargs['min_length'] = kwargs['max_length'] = kwargs.pop('length')
        self.min_length = kwargs.pop('min_length', None)
        super().__init__(*args, **kwargs)

    def coerce(self, value):
        if self.null and not value:
            return None
        return super().coerce(value)


class TextField(peewee.TextField):
    __data_type__ = str
    __schema_type__ = 'string'

    def coerce(self, value):
        if self.null and not value:
            return None
        return super().coerce(value)


class IntegerField(peewee.IntegerField):
    __data_type__ = int
    __schema_type__ = 'integer'

    def coerce(self, value):
        if not value:
            return None
        return super().coerce(value)


class HStoreField(postgres_ext.HStoreField):
    __data_type__ = dict
    __schema_type__ = 'object'

    def coerce(self, value):
        if isinstance(value, str):
            value = json.loads(value)
        return super().coerce(value)


class BinaryJSONField(postgres_ext.BinaryJSONField):
    __data_type__ = dict
    __schema_type__ = 'object'


class UUIDField(peewee.UUIDField):
    pass


class ArrayField(postgres_ext.ArrayField):
    __data_type__ = list
    __schema_type__ = 'array'

    def coerce(self, value):
        if not value:
            return []  # Coerce None to [].
        if value and not isinstance(value, (list, tuple)):
            value = [value]
        return value

    def python_value(self, value):
        return self.coerce(value)

    def db_value(self, value):
        if value is None:
            value = []
        return super().db_value(value)


class DateTimeField(postgres_ext.DateTimeTZField):
    __data_type__ = datetime
    __schema_type__ = 'string'
    __schema_format__ = 'date-time'

    def python_value(self, value):
        value = super().python_value(value)
        if value:
            # PSQL store dates in the server timezone, but we only want to
            # deal with UTC ones.
            return value.astimezone(timezone.utc)


class BooleanField(peewee.BooleanField):
    __data_type__ = bool
    __schema_type__ = 'boolean'


class FantoirField(CharField):

    max_length = 9

    def coerce(self, value):
        if not value:
            return None
        value = str(value)
        if len(value) == 10:
            value = value[:9]
        if not len(value) == 9:
            raise ValidationError('FANTOIR must be municipality INSEE + 4 '
                                  'first chars of FANTOIR, '
                                  'got `{}` instead'.format(value))
        return value


class ManyToManyField(fields.ManyToManyField):
    __data_type__ = list
    __schema_type__ = 'array'

    def __init__(self, *args, **kwargs):
        # ManyToManyField is not a real "Field", so try to better conform to
        # Field API.
        # https://github.com/coleifer/peewee/issues/794
        self.null = True
        self.unique = False
        self.index = False
        super().__init__(*args, **kwargs)

    def coerce(self, value, deleted=True, level1=0):
        from ban.core.resource import ResourceModel
        if not value:
            return []
        if not isinstance(value, (tuple, list, peewee.SelectQuery)):
            value = [value]
        value = [self.rel_model.coerce(item, None, level1) for item in value]
        for elem in value:
            if isinstance(elem, ResourceModel):
                if deleted is False and elem.deleted_at:
                    raise IsDeletedError(elem)
        return super().coerce(value)

    def add_to_class(self, model_class, name):
        # https://github.com/coleifer/peewee/issues/794
        model_class._meta.fields[name] = self
        super().add_to_class(model_class, name)


class NameField(CharField):
    def coerce(self, value):
        if not value:
            return None
        value = str(value)
        if value.isspace():
            raise ValidationError("Name must have non whitespace characters.");
        value = ' '.join(value.split()) #nettoyage des espaces multiples et en debut/fin de chaine

        return value


    def search(self, **kwargs):
        ponctuation = '[\.\(\)\[\]\"\'\-,;:\/]'
        articles = '(^| )((LA|L|LE|LES|DU|DE|DES|D|ET|A|AU) )*'
        if kwargs['type'] is None or kwargs['search'] is None:
            raise ValueError('None value for search.')
        if kwargs['type'] == 'strict':
            return peewee.Expression(self, peewee.OP.EQ, kwargs['search'])
        elif kwargs['type'] == 'case':
            return peewee.Expression(peewee.fn.unaccent(self), peewee.OP.ILIKE, peewee.fn.unaccent(kwargs['search']))
        elif kwargs['type'] == 'ponctuation':
            return peewee.Expression(
                peewee.fn.regexp_replace(peewee.fn.unaccent(self), ponctuation, ' ', 'g'),
                peewee.OP.ILIKE,
                peewee.fn.regexp_replace(peewee.fn.unaccent(kwargs['search']), ponctuation, ' ', 'g'))
        elif kwargs['type'] == 'abbrev':
            import csv
            abbrev = []
            with open('../../abbrev_type_voie.csv', newline='') as csvfile:
                csv = csv.reader(csvfile, delimiter=';')
                for row in csv:
                    if re.match(r"^{} ".format(row[1]),
                                re.sub(ponctuation, ' ', kwargs['search'].upper())) is not None \
                            or re.match(r"^{} ".format(row[0]),
                                        re.sub(ponctuation, ' ', kwargs['search'].upper())) is not None:
                        abbrev = row
                        break
                if not abbrev:
                    return peewee.Expression(
                        peewee.fn.regexp_replace(peewee.fn.unaccent(self), ponctuation, ' ', 'g'),
                        peewee.OP.ILIKE,
                        peewee.fn.regexp_replace(peewee.fn.unaccent(kwargs['search']), ponctuation, ' ', 'g'))
                return peewee.Expression(
                    peewee.fn.regexp_replace(
                        peewee.fn.regexp_replace(
                            peewee.fn.unaccent(peewee.fn.upper(self)), ponctuation, ' ', 'g'),
                        "^{} ".format(abbrev[1]), "{} ".format(abbrev[0]), 'g'),
                    peewee.OP.REGEXP,
                    peewee.fn.regexp_replace(
                        peewee.fn.regexp_replace(
                            peewee.fn.unaccent(peewee.fn.upper(kwargs['search'])), ponctuation, ' ', 'g'),
                        "^{} ".format(abbrev[1]), "{} ".format(abbrev[0]), 'g'))
        elif kwargs['type'] == 'libelle':
            import csv
            abbrev = '^('
            with open('../../abbrev_type_voie.csv', newline='') as csvfile:
                csv = csv.reader(csvfile, delimiter=';')
                for row in csv:
                    abbrev = '{}|{}|{}'.format(abbrev, row[0], row[1])
                abbrev = '{})( |$)'.format(abbrev)
                return peewee.Expression(
                    peewee.fn.regexp_replace(
                        peewee.fn.regexp_replace(
                            peewee.fn.unaccent(peewee.fn.upper(self)), ponctuation, ' ', 'g'),
                        abbrev, "", 'g'),
                    peewee.OP.ILIKE,
                    peewee.fn.regexp_replace(
                        peewee.fn.regexp_replace(
                            peewee.fn.unaccent(peewee.fn.upper(kwargs['search'])), ponctuation, ' ', 'g'),
                        abbrev, "", 'g'))
        elif kwargs['type'] == 'direct':
            import csv
            abbrev = '^('
            with open('../../abbrev_type_voie.csv', newline='') as csvfile:
                csv = csv.reader(csvfile, delimiter=';')
                for row in csv:
                    abbrev = '{}|{}|{}'.format(abbrev, row[0], row[1])
                abbrev = '{})( |$)'.format(abbrev)
                return peewee.Expression(
                    peewee.fn.trim(
                        peewee.fn.regexp_replace(
                            peewee.fn.regexp_replace(
                                peewee.fn.regexp_replace(
                                    peewee.fn.unaccent(peewee.fn.upper(self)),
                                    ponctuation, ' ', 'g'),
                                abbrev, "", 'g'),
                            articles, ' ', 'g')),
                    peewee.OP.ILIKE,
                    peewee.fn.trim(
                        peewee.fn.regexp_replace(
                            peewee.fn.regexp_replace(
                                peewee.fn.regexp_replace(
                                    peewee.fn.unaccent(peewee.fn.upper(kwargs['search'])),
                                    ponctuation, ' ', 'g'),
                                abbrev, "", 'g'),
                            articles, ' ', 'g')))
        elif kwargs['type'] == 'approx':
            import csv
            abbrev = '^('
            with open('../../abbrev_type_voie.csv', newline='') as csvfile:
                csv = csv.reader(csvfile, delimiter=';')
                for row in csv:
                    abbrev = '{}|{}|{}'.format(abbrev, row[0], row[1])
                abbrev = '{})( |$)'.format(abbrev)
                return peewee.Expression(
                    peewee.fn.levenshtein(
                        peewee.fn.trim(
                            peewee.fn.regexp_replace(
                                peewee.fn.regexp_replace(
                                    peewee.fn.regexp_replace(
                                        peewee.fn.unaccent(peewee.fn.upper(self)),
                                    ponctuation, ' ', 'g'),
                                abbrev, "", 'g'),
                            articles, ' ', 'g')),
                        peewee.fn.trim(
                            peewee.fn.regexp_replace(
                                peewee.fn.regexp_replace(
                                    peewee.fn.regexp_replace(
                                        peewee.fn.unaccent(peewee.fn.upper(kwargs['search'])),
                                        ponctuation, ' ', 'g'),
                                    abbrev, "", 'g'),
                                articles, ' ', 'g'))
                    ),
                    peewee.OP.LTE,
                    2)
        else:
            raise ValueError('Search type {} is unknown'.format(kwargs['type']))
