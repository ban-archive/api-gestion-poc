import re
from datetime import datetime

# from django.utils.translation import ugettext as _
import peewee
from unidecode import unidecode

from ban import db
from ban.auth.models import Session

from . import context
from .versioning import Versioned, BaseVersioned
from .resource import ResourceModel, BaseResource

__all__ = ['Municipality', 'Street', 'HouseNumber', 'Locality',
           'Position']


_ = lambda x: x


class BaseModel(BaseResource, BaseVersioned):
    pass


class TrackedModel(ResourceModel, Versioned, metaclass=BaseModel):
    # Allow null modified_by and created_by until proper auth management.
    created_at = db.DateTimeField()
    created_by = db.ForeignKeyField(Session)
    modified_at = db.DateTimeField()
    modified_by = db.ForeignKeyField(Session)

    class Meta:
        abstract = True
        validate_backrefs = False

    def save(self, *args, **kwargs):
        session = context.get('session')
        if session:
            try:
                getattr(self, 'created_by', None)
            except Session.DoesNotExist:
                # Field is not nullable, we can't access it when it's not yet
                # defined.
                self.created_by = session
            self.modified_by = session
        now = datetime.now()
        if not self.created_at:
            self.created_at = now
        self.modified_at = now
        super().save(*args, **kwargs)

    @classmethod
    def get_resource_fields(cls):
        return cls.resource_fields + ['id', 'version']


class NamedModel(TrackedModel):
    name = db.CharField(max_length=200, verbose_name=_("name"))

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ('name', )


class Municipality(NamedModel):
    resource_fields = ['name', 'insee', 'siren']

    insee = db.CharField(max_length=5)
    siren = db.CharField(max_length=9)


class BaseFantoirModel(NamedModel):
    resource_fields = ['name', 'fantoir', 'municipality']

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
    pass


class Street(BaseFantoirModel):
    pass


class HouseNumber(TrackedModel):
    resource_fields = ['number', 'ordinal', 'street', 'cia']

    number = db.CharField(max_length=16)
    ordinal = db.CharField(max_length=16, null=True)
    street = db.ForeignKeyField(Street, null=True)
    locality = db.ForeignKeyField(Locality, null=True)
    cia = db.CharField(max_length=100)

    class Meta:
        # Does not work, as SQL does not consider NULL has values. Is there
        # any way to enforce that at the DB level anyway?
        unique_together = ('number', 'ordinal', 'street', 'locality')
        resource_schema = {'cia': {'required': False}}

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
        if HouseNumber.select().where(HouseNumber.number == self.number,
                                      HouseNumber.ordinal == self.ordinal,
                                      HouseNumber.street == self.street,
                                      HouseNumber.locality == self.locality).exists():
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
        return position.center_json if position else None


class Position(TrackedModel):
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
    def center_json(self):
        return {'lat': self.center[1], 'lon': self.center[0]}
