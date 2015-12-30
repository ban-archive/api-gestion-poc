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

    class Meta:
        validate_backrefs = False
        # 'version' is validated by us.
        resource_schema = {'version': {'required': False}}

    @classmethod
    def get_resource_fields(cls):
        return cls.resource_fields + ['id', 'version']


class NamedModel(Model):
    name = db.CharField(max_length=200)
    alias = db.ArrayField(db.CharField, null=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ('name', )


class PostCode(Model):
    identifiers = ['code']
    resource_fields = ['code', 'municipalities']
    code = db.PostCodeField()


class Municipality(NamedModel):
    identifiers = ['siren', 'insee']
    resource_fields = ['name', 'alias', 'insee', 'siren', 'postcodes']

    insee = db.CharField(max_length=5, unique=True)
    siren = db.CharField(max_length=9, unique=True)
    postcodes = db.ManyToManyField(PostCode, related_name='municipalities')

    @property
    def postcodes_resource(self):
        return [p.code for p in self.postcodes]


class District(NamedModel):
    """Submunicipal non administrative area."""
    resource_fields = ['name', 'alias', 'attributes', 'municipality']

    attributes = db.HStoreField(null=True)
    municipality = db.ForeignKeyField(Municipality)


class BaseFantoirModel(NamedModel):
    identifiers = ['fantoir']
    resource_fields = ['name', 'alias', 'fantoir', 'municipality']

    fantoir = db.CharField(max_length=9, null=True)
    municipality = db.ForeignKeyField(Municipality)

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
    resource_fields = ['number', 'ordinal', 'street', 'cia', 'laposte',
                       'districts', 'center', 'locality', 'postcode']

    number = db.CharField(max_length=16)
    ordinal = db.CharField(max_length=16, null=True)
    street = db.ForeignKeyField(Street, null=True)
    locality = db.ForeignKeyField(Locality, null=True)
    cia = db.CharField(max_length=100)
    laposte = db.CharField(max_length=10, null=True)
    postcode = db.ForeignKeyField(PostCode, null=True)
    districts = db.ManyToManyField(District, related_name='housenumbers')

    class Meta:
        resource_schema = {'cia': {'required': False},
                           'version': {'required': False}}
        order_by = ('number', 'ordinal')

    def __str__(self):
        return ' '.join([self.number, self.ordinal])

    @property
    def parent(self):
        return self.street or self.locality

    def save(self, *args, **kwargs):
        if not getattr(self, '_clean_called', False):
            self.clean()
        self.cia = self.compute_cia()
        super().save(*args, **kwargs)
        self._clean_called = False

    def clean(self):
        if not self.street and not self.locality:
            raise ValueError('A housenumber number needs to be linked to either a street or a locality.')  # noqa
        qs = HouseNumber.select().where(HouseNumber.number == self.number,
                                        HouseNumber.ordinal == self.ordinal,
                                        HouseNumber.street == self.street,
                                        HouseNumber.locality == self.locality)
        if self.id:
            qs = qs.where(HouseNumber.id != self.id)
        if qs.exists():
            raise ValueError('Row with same number, ordinal, street and locality already exists')  # noqa
        self._clean_called = True

    def compute_cia(self):
        return '_'.join([
            str(self.parent.municipality.insee),
            self.street.get_fantoir() if self.street else '',
            self.locality.get_fantoir() if self.locality else '',
            self.number.upper(),
            self.ordinal.upper()
        ])

    @property
    def center(self):
        position = self.position_set.first()
        return position.center.geojson if position else None

    @property
    def districts_resource(self):
        return [d.as_relation for d in self.districts]

    @property
    def postcode_resource(self):
        return self.postcode.code if self.postcode else None


class Position(Model):
    resource_fields = ['center', 'source', 'housenumber', 'attributes',
                       'kind', 'comment']

    center = db.PointField(verbose_name=_("center"))
    housenumber = db.ForeignKeyField(HouseNumber)
    source = db.CharField(max_length=64, null=True)
    kind = db.CharField(max_length=64, null=True)
    attributes = db.HStoreField(null=True)
    comment = peewee.TextField(null=True)

    class Meta:
        unique_together = ('housenumber', 'source')

    @property
    def center_resource(self):
        if not isinstance(self.center, Point):
            self.center = Point(*self.center)
        return self.center.geojson
