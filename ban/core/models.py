from datetime import datetime
import re

from unidecode import unidecode

# from django.utils.translation import ugettext as _
import peewee
from playhouse.postgres_ext import HStoreField

from ban.versioning.models import VersionMixin
from ban.core import context
from .database import db
from .fields import HouseNumberField


_ = lambda x: x



class ResourceQueryResultWrapper(peewee.ModelQueryResultWrapper):

    def process_row(self, row):
        instance = super().process_row(row)
        return instance.as_resource


class SelectQuery(peewee.SelectQuery):

    def _get_result_wrapper(self):
        if getattr(self, '_as_resource', False):
            return ResourceQueryResultWrapper
        else:
            return super()._get_result_wrapper()

    @peewee.returns_clone
    def as_resource(self):
        self._as_resource = True

    def __len__(self):
        return self.count()


class ResourceModel(peewee.Model):
    json_fields = []

    class Meta:
        abstract = True

    # TODO find a way not to override the peewee.Model select classmethod.
    @classmethod
    def select(cls, *selection):
        query = SelectQuery(cls, *selection)
        if cls._meta.order_by:
            query = query.order_by(*cls._meta.order_by)
        return query

    def get_json_fields(self):
        return self.json_fields + ['id', 'version']

    @property
    def as_resource(self):
        return {f: self.as_resource_field(f) for f in self.get_json_fields()}

    @property
    def as_relation(self):
        return {f: self.as_relation_field(f) for f in self.get_json_fields()}

    def as_resource_field(self, name):
        value = getattr(self, '{}_json'.format(name), getattr(self, name))
        return getattr(value, 'as_relation', value)

    def as_relation_field(self, name):
        value = getattr(self, name)
        return getattr(value, 'pk', value)


class Contact(ResourceModel):

    username = peewee.CharField(verbose_name=_('Company'), max_length=100)
    email = peewee.CharField(verbose_name=_('Company'), max_length=100)
    company = peewee.CharField(verbose_name=_('Company'), max_length=100,
                               null=True)

    class Meta:
        database = db

    def set_password(self, password):
        pass


class TrackedModel(peewee.Model):
    # Allow null modified_by and created_by until proper auth management.
    created_at = peewee.DateTimeField()
    created_by = peewee.ForeignKeyField(Contact, null=True)
    modified_at = peewee.DateTimeField()
    modified_by = peewee.ForeignKeyField(Contact, null=True)

    class Meta:
        abstract = True
        database = db
        validate_backrefs = False

    def save(self, *args, **kwargs):
        user = context.get_user()
        if user and user.is_authenticated():
            if not getattr(self, 'created_by', None):
                self.created_by = user
            self.modified_by = user
        now = datetime.now()
        if not self.created_at:
            self.created_at = now
        self.modified_at = now
        super().save(*args, **kwargs)


class NamedModel(TrackedModel):
    name = peewee.CharField(max_length=200, verbose_name=_("name"))

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ('name', )


class Municipality(NamedModel, VersionMixin, ResourceModel):
    json_fields = ['name', 'insee', 'siren']

    insee = peewee.CharField(max_length=5)
    siren = peewee.CharField(max_length=9)


class BaseFantoirModel(NamedModel, VersionMixin, ResourceModel):
    json_fields = ['name', 'fantoir', 'municipality']

    fantoir = peewee.CharField(max_length=9, null=True)
    municipality = peewee.ForeignKeyField(Municipality)

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


class HouseNumber(TrackedModel, VersionMixin, ResourceModel):
    json_fields = ['number', 'ordinal', 'street', 'cia', 'center']

    number = peewee.CharField(max_length=16)
    ordinal = peewee.CharField(max_length=16)
    street = peewee.ForeignKeyField(Street, null=True)
    locality = peewee.ForeignKeyField(Locality, null=True)
    cia = peewee.CharField(max_length=100)

    class Meta:
        # Does not work, as SQL does not consider NULL has values. Is there
        # any way to enforce that at the DB level anyway?
        unique_together = ('number', 'ordinal', 'street', 'locality')

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


class Position(TrackedModel, VersionMixin, ResourceModel):
    json_fields = ['center', 'source', 'housenumber']

    center = HouseNumberField(verbose_name=_("center"))
    housenumber = peewee.ForeignKeyField(HouseNumber)
    source = peewee.CharField(max_length=64, null=True)
    kind = peewee.CharField(max_length=64, null=True)
    attributes = HStoreField(null=True)
    comment = peewee.TextField(null=True)

    class Meta:
        unique_together = ('housenumber', 'source')

    @property
    def center_json(self):
        return {'lat': self.center[1], 'lon': self.center[0]}
