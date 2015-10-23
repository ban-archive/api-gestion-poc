import re

from unidecode import unidecode

from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models
from django.contrib.postgres.fields import HStoreField
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from ban.versioning.models import VersionMixin
from ban.core import context
from .fields import HouseNumberField


class User(AbstractUser):

    company = models.CharField(_('Company'), max_length=100, blank=True)


class TrackedModel(models.Model):
    # Allow null modified_by and created_by until proper auth management.
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='%(class)s_created',
                                   editable=False, null=True)
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, editable=False, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = context.get_user()
        if user and user.is_authenticated():
            if not getattr(self, 'created_by', None):
                self.created_by = user
            self.modified_by = user
        super().save(*args, **kwargs)


class ResourceQuerySet(models.QuerySet):

    def iterator(self):
        for item in super().iterator():
            yield item.as_resource


class ResourceManager(models.Manager):
    use_for_related_fields = True

    @property
    def as_resource(self):
        return self.get_queryset()._clone(klass=ResourceQuerySet)


class ResourceModel(models.Model):
    json_fields = []

    objects = ResourceManager()

    class Meta:
        abstract = True

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


class NamedModel(TrackedModel):
    name = models.CharField(max_length=200, verbose_name=_("name"))

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ('name', )


class Municipality(NamedModel, VersionMixin, ResourceModel):
    json_fields = ['name', 'insee', 'siren']

    insee = models.CharField(max_length=5)
    siren = models.CharField(max_length=9)


class BaseFantoirModel(NamedModel, VersionMixin, ResourceModel):
    json_fields = ['name', 'fantoir', 'municipality']

    fantoir = models.CharField(max_length=9, blank=True, null=True)
    municipality = models.ForeignKey(Municipality)

    class Meta:
        abstract = True

    @property
    def tmp_fantoir(self):
        return '#' + re.sub(r'[\W]', '', unidecode(self.name)).upper()


class Locality(BaseFantoirModel):
    pass


class Street(BaseFantoirModel):
    pass


class HouseNumber(TrackedModel, VersionMixin, ResourceModel):
    json_fields = ['number', 'ordinal', 'street', 'cia', 'center']

    number = models.CharField(max_length=16)
    ordinal = models.CharField(max_length=16, blank=True)
    street = models.ForeignKey(Street, blank=True, null=True)
    locality = models.ForeignKey(Locality, blank=True, null=True)
    cia = models.CharField(max_length=100, blank=True, editable=False)

    class Meta:
        # Does not work, as SQL does not consider NULL has values. Is there
        # any way to enforce that at the DB level anyway?
        unique_together = ('number', 'ordinal', 'street', 'locality')

    def __str__(self):
        return ' '.join([self.number, self.ordinal])

    def save(self, *args, **kwargs):
        if not getattr(self, '_clean_called', False):
            self.clean()
        self.cia = self.compute_cia()
        super().save(*args, **kwargs)
        self._clean_called = False

    def clean(self):
        if not self.street and not self.locality:
            raise ValidationError('A housenumber number needs to be linked to '
                                  'either a street or a locality.')
        if HouseNumber.objects.filter(number=self.number, ordinal=self.ordinal,
                                      street=self.street,
                                      locality=self.locality).exists():
            raise ValidationError('Row with same number, ordinal, street and '
                                  'locality already exists')
        self._clean_called = True

    def compute_cia(self):
        return '_'.join([
            str(self.street.municipality.insee),
            self.street.fantoir or self.street.tmp_fantoir,
            self.number.upper(),
            self.ordinal.upper()
        ])

    @property
    def center(self):
        position = self.position_set.first()
        return position.center_json if position else None


class Position(TrackedModel, VersionMixin, ResourceModel):
    json_fields = ['center', 'source', 'housenumber']

    center = HouseNumberField(geography=True, verbose_name=_("center"))
    housenumber = models.ForeignKey(HouseNumber)
    source = models.CharField(max_length=64, blank=True)
    kind = models.CharField(max_length=64, blank=True)
    attributes = HStoreField(blank=True, null=True)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('housenumber', 'source')

    @property
    def center_json(self):
        return {'lat': self.center.coords[1], 'lon': self.center.coords[0]}
