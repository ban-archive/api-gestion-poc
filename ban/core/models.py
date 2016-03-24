import re

import peewee
from postgis import Point
from unidecode import unidecode

from ban import db
from .versioning import Versioned, BaseVersioned
from .resource import ResourceModel, BaseResource

__all__ = ['Municipality', 'Group', 'HouseNumber', 'PostCode',
           'Position']


_ = lambda x: x


class BaseModel(BaseResource, BaseVersioned):
    pass


class Model(ResourceModel, Versioned, metaclass=BaseModel):
    resource_fields = ['version']

    class Meta:
        validate_backrefs = False
        # 'version' is validated by us.
        resource_schema = {'version': {'required': False},
                           'id': {'required': False}}


class NamedModel(Model):
    name = db.CharField(max_length=200)
    alias = db.ArrayField(db.CharField, null=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ('name', )


class Municipality(NamedModel):
    identifiers = ['siren', 'insee']
    resource_fields = ['name', 'alias', 'insee', 'siren', 'postcodes']

    insee = db.CharField(max_length=5, unique=True)
    siren = db.CharField(max_length=9, unique=True)

    @property
    def postcodes_resource(self):
        return [p.code for p in self.postcodes]


class BaseGroup(NamedModel):
    municipality = db.ForeignKeyField(Municipality,
                                      related_name='{classname}s')
    attributes = db.HStoreField(null=True)

    class Meta:
        abstract = True

    @property
    def housenumbers(self):
        qs = (self._housenumbers | self.housenumber_set)
        return qs.order_by(peewee.SQL('number'), peewee.SQL('ordinal'))


class PostCode(BaseGroup):
    identifiers = ['code']
    resource_fields = ['code', 'name', 'municipality']
    code = db.PostCodeField(index=True)

    class Meta:
        indexes = (
            (('code', 'municipality'), True),
        )


class Group(BaseGroup):
    AREA = 'area'
    WAY = 'way'
    KIND = (
        (WAY, 'way'),
        (AREA, 'area'),
    )
    identifiers = ['fantoir', 'laposte', 'ign']
    resource_fields = ['name', 'alias', 'fantoir', 'attributes',
                       'municipality', 'kind', 'laposte', 'ign']

    kind = db.CharField(max_length=64, choices=KIND)
    fantoir = db.CharField(max_length=9, null=True, unique=True)
    laposte = db.CharField(max_length=10, null=True, unique=True)
    ign = db.CharField(max_length=24, null=True, unique=True)

    @property
    def tmp_fantoir(self):
        return '#' + re.sub(r'[\W]', '', unidecode(self.name)).upper()

    def get_fantoir(self):
        return self.fantoir or self.tmp_fantoir


class HouseNumber(Model):
    identifiers = ['cia', 'laposte', 'ign']
    resource_fields = ['number', 'ordinal', 'parent', 'cia', 'laposte',
                       'ancestors', 'center', 'ign', 'postcodes']

    number = db.CharField(max_length=16)
    ordinal = db.CharField(max_length=16, null=True)
    parent = db.ForeignKeyField(Group)
    cia = db.CharField(max_length=100, null=True, index=True)
    laposte = db.CharField(max_length=10, null=True, unique=True)
    ign = db.CharField(max_length=24, null=True, unique=True)
    ancestors = db.ManyToManyField(Group, related_name='_housenumbers')
    postcodes = db.ManyToManyField(PostCode, related_name='_housenumbers')

    class Meta:
        resource_schema = {'cia': {'required': False},
                           'version': {'required': False},
                           'id': {'required': False}}
        order_by = ('number', 'ordinal')
        indexes = (
            (('parent', 'number', 'ordinal'), True),
        )

    def __str__(self):
        return ' '.join([self.number, self.ordinal])

    def save(self, *args, **kwargs):
        # if not getattr(self, '_clean_called', False):
        #     self.clean()
        self.cia = self.compute_cia()
        super().save(*args, **kwargs)
        self._clean_called = False

    def clean(self):
        if not self.street and not self.locality:
            raise ValueError('A housenumber number needs to be linked to '
                             'either a street or a locality.')
        qs = HouseNumber.select().where(HouseNumber.number == self.number,
                                        HouseNumber.ordinal == self.ordinal,
                                        HouseNumber.street == self.street,
                                        HouseNumber.locality == self.locality)
        if self.pk:
            qs = qs.where(HouseNumber.pk != self.pk)
        if qs.exists():
            raise ValueError('Row with same number, ordinal, street and '
                             'locality already exists')
        self._clean_called = True

    def compute_cia(self):
        get_fantoir = getattr(self.parent, 'get_fantoir', None)
        if not get_fantoir:
            return None
        return '_'.join([
            str(self.parent.municipality.insee),
            get_fantoir(),
            (self.number or '').upper(),
            (self.ordinal or '').upper()
        ])

    @property
    def center(self):
        position = self.position_set.first()
        return position.center.geojson if position else None

    @property
    def ancestors_resource(self):
        return [d.as_list for d in self.ancestors]

    @property
    def postcodes_resource(self):
        return [d.as_list for d in self.postcodes]


class Position(Model):

    POSTAL = 'postal'
    ENTRANCE = 'entrance'
    BUILDING = 'building'
    STAIRCASE = 'staircase'
    UNIT = 'unit'
    PARCEL = 'parcel'
    SEGMENT = 'segment'
    UTILITY = 'utility'
    KIND = (
        (POSTAL, _('postal delivery')),
        (ENTRANCE, _('entrance')),
        (BUILDING, _('building')),
        (STAIRCASE, _('staircase identifier')),
        (UNIT, _('unit identifier')),
        (PARCEL, _('parcel')),
        (SEGMENT, _('road segment')),
        (UTILITY, _('utility service')),
    )

    DGPS = 'dgps'
    GPS = 'gps'
    IMAGERY = 'imagery'
    PROJECTION = 'projection'
    INTERPOLATION = 'interpolation'
    OTHER = 'other'
    POSITIONING = (
        (DGPS, _('via differencial GPS')),
        (GPS, _('via GPS')),
        (IMAGERY, _('via imagery')),
        (PROJECTION, _('computed via projection')),
        (INTERPOLATION, _('computed via interpolation')),
        (OTHER, _('other')),
    )

    resource_fields = ['center', 'source', 'housenumber', 'attributes',
                       'kind', 'comment', 'parent', 'positioning']

    center = db.PointField(verbose_name=_("center"))
    housenumber = db.ForeignKeyField(HouseNumber)
    parent = db.ForeignKeyField('self', related_name='children', null=True)
    source = db.CharField(max_length=64, null=True)
    kind = db.CharField(max_length=64, choices=KIND)
    positioning = db.CharField(max_length=32, choices=POSITIONING)
    attributes = db.HStoreField(null=True)
    comment = peewee.TextField(null=True)

    class Meta:
        unique_together = ('housenumber', 'source')

    @property
    def center_resource(self):
        if not isinstance(self.center, Point):
            self.center = Point(*self.center)
        return self.center.geojson
