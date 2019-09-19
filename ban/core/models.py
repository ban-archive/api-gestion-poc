import peewee
from werkzeug.utils import cached_property

from ban import db
from ban.utils import compute_cia
from .versioning import Versioned, BaseVersioned, Version
from .resource import ResourceModel, BaseResource
from .validators import VersionedResourceValidator

__all__ = ['Municipality', 'Group', 'HouseNumber', 'PostCode',
           'Position']


_ = lambda x: x


class ModelBase(BaseResource, BaseVersioned):
    pass


class Model(ResourceModel, Versioned, metaclass=ModelBase):
    resource_fields = ['version', 'created_at', 'created_by', 'modified_at',
                       'modified_by', 'attributes']
    exclude_for_collection = ['created_at', 'created_by',
                              'modified_at', 'modified_by']
    readonly_fields = (ResourceModel.readonly_fields + ['created_at',
                       'created_by', 'modified_at', 'modified_by'])

    attributes = db.HStoreField(null=True)

    class Meta:
        validator = VersionedResourceValidator
        case_ignoring = ()
        reverse_relation_ignoring = ()


class NamedModel(Model):
    name = db.NameField(max_length=200)
    alias = db.ArrayField(db.CharField, default=[], null=True)

    def __str__(self):
        return self.name


class Municipality(NamedModel):
    INSEE_FORMAT = '(2[AB]|\d{2})\d{3}'
    identifiers = ['siren', 'insee']
    resource_fields = ['name', 'alias', 'insee', 'siren']
    exclude_for_version = ['postcodes']

    insee = db.CharField(length=5, unique=True, format=INSEE_FORMAT)
    siren = db.CharField(length=9, format='\d*', unique=True, null=True)

    @property
    def municipality(self):
        return self


class PostCode(NamedModel):
    resource_fields = ['code', 'name', 'alias', 'complement', 'municipality']

    complement = db.CharField(max_length=38, null=True)
    code = db.CharField(index=True, format='\d*', length=5)
    municipality = db.CachedForeignKeyField(Municipality,
                                            backref='postcodes')

    class Meta:
        indexes = (
            (('code', 'complement', 'municipality'), True),
        )

    @property
    def housenumbers(self):
        return self.housenumber_set.order_by(
            peewee.SQL('number ASC NULLS FIRST'),
            peewee.SQL('ordinal ASC NULLS FIRST'))


class Group(NamedModel):
    AREA = 'area'
    WAY = 'way'
    KIND = (
        (WAY, 'way'),
        (AREA, 'area'),
    )
    CLASSICAL = 'classical'
    METRIC = 'metric'
    LINEAR = 'linear'
    MIXED = 'mixed'
    ANARCHICAL = 'anarchical'
    ADDRESSING = (
        (CLASSICAL, 'classical'),
        (METRIC, 'metric'),
        (LINEAR, 'linear'),
        (MIXED, 'mixed types'),
        (ANARCHICAL, 'anarchical'),
    )
    identifiers = ['fantoir', 'laposte', 'ign']
    resource_fields = ['name', 'alias', 'fantoir', 'municipality', 'kind',
                       'laposte', 'ign', 'addressing']

    kind = db.CharField(max_length=64, choices=KIND)
    addressing = db.CharField(max_length=16, choices=ADDRESSING, null=True)
    fantoir = db.FantoirField(null=True, unique=True)
    laposte = db.CharField(max_length=8, null=True, unique=True, format='\d*')
    ign = db.CharField(max_length=24, null=True, unique=True)
    municipality = db.CachedForeignKeyField(Municipality,
                                            backref='groups')

    @property
    def housenumbers(self):
        qs = (self._housenumbers | self.housenumber_set)
        return qs.order_by(peewee.SQL('number ASC NULLS FIRST'),
                           peewee.SQL('ordinal ASC NULLS FIRST'))


    def merge(self, erased_group, prior="master"):
        master_hn = {}
        for hn in self.housenumbers:
            uniq_key = "{}_{}".format(hn.number, hn.ordinal)
            master_hn[uniq_key] = hn

        # hn merge
        for hn in erased_group.housenumbers:
            if hn.deleted_at:
                continue
            uniq_key = "{}_{}".format(hn.number, hn.ordinal)
            if uniq_key in master_hn.keys():
                master_hn[uniq_key].merge(hn, prior)
            else:
                hn.parent = self
                hn.increment_version()
                hn.save()

        # ids management
        for id in self.identifiers:
            if not getattr(self, id):
                setattr(self, id, getattr(erased_group, id))

        erased_group.mark_deleted()
        self.increment_version()
        self.save()


class HouseNumber(Model):
    # INSEE + set of OCR-friendly characters (dropped confusing ones
    # (like 0/O, 1/I…)) from La Poste.
    CEA_FORMAT = Municipality.INSEE_FORMAT + '[234679ABCEGHILMNPRSTUVXYZ]{5}'
    identifiers = ['cia', 'laposte', 'ign']
    resource_fields = ['number', 'ordinal', 'parent', 'cia', 'laposte',
                       'ancestors', 'ign', 'postcode']
    exclude_for_collection = ['ancestors']

    number = db.CharField(max_length=16, null=True)
    ordinal = db.CharField(max_length=16, null=True)
    parent = db.ForeignKeyField(Group)
    cia = db.CharField(max_length=100, null=True, unique=True)
    laposte = db.CharField(length=10, null=True, unique=True,
                           format=CEA_FORMAT)
    ign = db.CharField(max_length=24, null=True, unique=True)
    ancestors = db.ManyToManyField(Group, backref='_housenumbers')
    postcode = db.CachedForeignKeyField(PostCode, null=True)

    class Meta:
        indexes = (
            (('parent', 'number', 'ordinal'), True),
        )
        case_ignoring = ('ordinal',)
        reverse_relation_ignoring = ('housenumbergroupthrough_set',)  # don't check these relations when mark as deleted

    def __str__(self):
        return ' '.join([self.number or '', self.ordinal or ''])

    def save(self, *args, **kwargs):
        self.cia = self.compute_cia()
        super().save(*args, **kwargs)
        self._clean_called = False

    def compute_cia(self):
        return compute_cia(self.parent.fantoir[:5],
                           self.parent.fantoir[5:],
                           self.number, self.ordinal) if self.parent.fantoir else None

    @cached_property
    def municipality(self):
        return Municipality.select().where(
           Municipality.pk == self.parent.municipality.pk).first()

    @property
    def as_export(self):
        """Resources plus relation references without metadata."""
        mask = {f: {} for f in self.resource_fields}
        return self.serialize(mask)


    def merge(self, erased_hn, prior="master"):
        # merge position
        # keep all positions with different kind/source_kind/name
        # keep prior position if same values
        master_pos = {}
        to_up = []
        to_del_keys = []
        for pos in self.positions:
            if pos.deleted_at:
                continue
            uniq_key = "{}_{}_{}".format(pos.kind, pos.source_kind, pos.name)
            if uniq_key not in master_pos.keys():
                master_pos[uniq_key] = []
            master_pos[uniq_key].append(pos)
        for pos in erased_hn.positions:
            if pos.deleted_at:
                continue
            uniq_key = "{}_{}_{}".format(pos.kind, pos.source_kind, pos.name)
            if uniq_key in master_pos.keys() and prior == "erased":
                to_up.append(pos)
                to_del_keys.append(uniq_key)
            elif uniq_key in master_pos.keys() and prior == "master":
                pos.mark_deleted()
            else:
                to_up.append(pos)
        for pos in to_up:
            pos.housenumber = self
            pos.increment_version()
            pos.save()
        for key in to_del_keys:
            for pos in master_pos[key]:
                pos.mark_deleted()

        # ids and postcode management
        for id in self.identifiers:
            if not getattr(self, id):
                setattr(self, id, getattr(erased_hn, id))
        if not self.postcode:
            self.postcode = erased_hn.postcode

        # merge ancestors
        self.ancestors.add(erased_hn.ancestors)

        # delete erased_hn
        erased_hn.mark_deleted()
        self.deleted_at = None
        self.increment_version()
        self.save()


class Position(Model):

    POSTAL = 'postal'
    ENTRANCE = 'entrance'
    BUILDING = 'building'
    STAIRCASE = 'staircase'
    UNIT = 'unit'
    PARCEL = 'parcel'
    SEGMENT = 'segment'
    UTILITY = 'utility'
    UNKNOWN = 'unknown'
    AREA = 'area'
    KIND = (
        (POSTAL, _('postal delivery')),
        (ENTRANCE, _('entrance')),
        (BUILDING, _('building')),
        (STAIRCASE, _('staircase identifier')),
        (UNIT, _('unit identifier')),
        (PARCEL, _('parcel')),
        (SEGMENT, _('road segment')),
        (UTILITY, _('utility service')),
        (AREA, _('area')),
        (UNKNOWN, _('unknown')),
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

    identifiers = ['laposte', 'ign']
    resource_fields = ['center', 'source', 'housenumber', 'kind', 'comment',
                       'parent', 'positioning', 'name', 'ign', 'laposte', 'source_kind']
    readonly_fields = Model.readonly_fields + ['source_kind']

    name = db.CharField(max_length=200, null=True)
    center = db.PointField(verbose_name=_("center"), null=True, index=True)
    housenumber = db.ForeignKeyField(HouseNumber, backref='positions')
    parent = db.ForeignKeyField('self', backref='children', null=True)
    source = db.CharField(max_length=64, null=True)
    kind = db.CharField(max_length=64, choices=KIND)
    positioning = db.CharField(max_length=32, choices=POSITIONING)
    ign = db.CharField(max_length=24, null=True, unique=True)
    laposte = db.CharField(length=10, null=True, unique=True,
                           format=HouseNumber.CEA_FORMAT)
    comment = db.TextField(null=True)
    source_kind = db.CharField()

    @classmethod
    def validate(cls, validator, document, instance):
        errors = {}
        default = instance and validator.update and instance.name
        name = document.get('name', default)
        default = instance and validator.update and instance.center
        center = document.get('center', default)
        if not name and not center:
            msg = 'A position must have either a center or a name.'
            errors['center'] = msg
            errors['name'] = msg
        return errors

    @cached_property
    def municipality(self):
        return Municipality.select().where(Municipality.pk == self.housenumber.parent.municipality.pk).first()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._clean_called = False
