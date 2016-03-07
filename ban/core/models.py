import re

import peewee
from postgis import Point
from unidecode import unidecode

from ban import db
from .versioning import Versioned, BaseVersioned
from .resource import ResourceModel, BaseResource

__all__ = ['Municipality', 'Street', 'HouseNumber', 'Locality',
           'Position']


_ = lambda x: x


class BaseModel(BaseResource, BaseVersioned):
    pass


class Model(ResourceModel, Versioned, metaclass=BaseModel):

    resource_fields = ['version']

    class Meta:
        validate_backrefs = False
        # 'version' is validated by us.
        resource_schema = {'version': {'required': False}}


class NamedModel(Model):
    name = db.CharField(max_length=200)
    alias = db.ArrayField(db.CharField, null=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ('name', )


class Proxy(db.Model):
    kind = db.CharField(max_length=50, null=False)

    @property
    def real(self):
        # Make dynamic.
        mapping = {class_.__name__.lower(): class_
                   for class_ in [Street, Locality, PostCode, District]}
        class_ = mapping[self.kind]
        return class_.get(class_.proxy == self)


class Municipality(NamedModel):
    identifiers = ['siren', 'insee']
    resource_fields = ['name', 'alias', 'insee', 'siren', 'postcodes']

    insee = db.CharField(max_length=5, unique=True)
    siren = db.CharField(max_length=9, unique=True)

    @property
    def postcodes_resource(self):
        return [p.code for p in self.postcodes]


class ProxyableModel(Model):
    proxy = db.ForeignKeyField(Proxy, unique=True)
    municipality = db.ForeignKeyField(Municipality,
                                      related_name='{classname}s')
    attributes = db.HStoreField(null=True)

    class Meta:
        auto_increment = False

    @property
    def housenumbers(self):
        qs = (self.proxy.housenumbers | self.proxy.housenumber_set)
        return qs.order_by(peewee.SQL('number'), peewee.SQL('ordinal'))

    def save(self, *args, **kwargs):
        if not self.id:
            proxy = Proxy(kind=self.resource)
            proxy.save()
            self.proxy = proxy.id
            self.id = proxy.id
            kwargs['force_insert'] = True
        return super().save(*args, **kwargs)

    def delete_instance(self, recursive=False, delete_nullable=False):
        with self._meta.database.atomic():
            super().delete_instance(recursive, delete_nullable)
            self.proxy.delete_instance()


class PostCode(ProxyableModel):
    identifiers = ['code']
    resource_fields = ['code', 'municipality']
    code = db.PostCodeField()

    class Meta:
        indexes = (
            (('code', 'municipality'), True),
        )


class District(ProxyableModel, NamedModel):
    """Submunicipal non administrative area."""
    resource_fields = ['name', 'alias', 'attributes', 'municipality']


class BaseFantoirModel(ProxyableModel, NamedModel):
    identifiers = ['fantoir']
    resource_fields = ['name', 'alias', 'fantoir', 'municipality']

    fantoir = db.CharField(max_length=9, null=True)

    class Meta:
        abstract = True

    @property
    def tmp_fantoir(self):
        return '#' + re.sub(r'[\W]', '', unidecode(self.name)).upper()

    def get_fantoir(self):
        return self.fantoir or self.tmp_fantoir


class Locality(BaseFantoirModel):
    """Any area referenced with a Fantoir."""
    pass


class Street(BaseFantoirModel):
    pass


class HouseNumber(Model):
    identifiers = ['cia']
    resource_fields = ['number', 'ordinal', 'parent', 'cia', 'laposte',
                       'ancestors', 'center', 'ign']

    number = db.CharField(max_length=16)
    ordinal = db.CharField(max_length=16, null=True)
    parent = db.ProxyField(Proxy)
    cia = db.CharField(max_length=100, null=True)
    laposte = db.CharField(max_length=10, null=True)
    ign = db.CharField(max_length=24, null=True)
    ancestors = db.ProxiesField(Proxy, related_name='housenumbers')

    class Meta:
        resource_schema = {'cia': {'required': False},
                           'version': {'required': False}}
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
        if self.id:
            qs = qs.where(HouseNumber.id != self.id)
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
            self.number.upper(),
            self.ordinal.upper()
        ])

    @property
    def center(self):
        position = self.position_set.first()
        return position.center.geojson if position else None

    @property
    def ancestors_resource(self):
        return [d.as_relation for d in self.ancestors]


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

    resource_fields = ['center', 'source', 'housenumber', 'attributes',
                       'kind', 'comment', 'parent']

    center = db.PointField(verbose_name=_("center"))
    housenumber = db.ForeignKeyField(HouseNumber)
    parent = db.ForeignKeyField('self', related_name='children', null=True)
    source = db.CharField(max_length=64, null=True)
    kind = db.CharField(max_length=64, choices=KIND)
    attributes = db.HStoreField(null=True)
    comment = peewee.TextField(null=True)

    class Meta:
        unique_together = ('housenumber', 'source')

    @property
    def center_resource(self):
        if not isinstance(self.center, Point):
            self.center = Point(*self.center)
        return self.center.geojson
