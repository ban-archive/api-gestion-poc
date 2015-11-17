from datetime import datetime
import pickle

import peewee

from ban import db
from ban.auth.models import Session

from . import context


class ForcedVersionError(Exception):
    pass


class BaseVersioned(peewee.BaseModel):

    registry = {}

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs, **kwargs)
        BaseVersioned.registry[name] = cls
        return cls


class Versioned(db.Model, metaclass=BaseVersioned):

    ForcedVersionError = ForcedVersionError

    version = db.IntegerField(default=1)
    created_at = db.DateTimeField()
    created_by = db.ForeignKeyField(Session)
    modified_at = db.DateTimeField()
    modified_by = db.ForeignKeyField(Session)

    class Meta:
        abstract = True
        validate_backrefs = False
        unique_together = ('id', 'version')

    @classmethod
    def get(cls, *query, **kwargs):
        instance = super().get(*query, **kwargs)
        instance.lock_version()
        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_version()

    def _serialize(self, fields):
        data = {}
        for field in fields:
            value = getattr(self, field.name)
            if isinstance(value, peewee.Model):
                value = value.id
            data[field.name] = value
        return data

    def serialize(self, fields=None):
        return pickle.dumps(self._serialize(self._meta.get_fields()))

    def store_version(self):
        old = None
        if self.version > 1:
            old = self.load_version(self.version - 1)
        new = Version.create(
            model=self.__class__.__name__,
            model_id=self.id,
            sequential=self.version,
            data=self.serialize()
        )
        if Diff.ACTIVE:
            Diff.create(old=old, new=new, created_at=self.modified_at)

    @property
    def versions(self):
        return Version.select().where(Version.model == self.__class__.__name__,
                                      Version.model_id == self.id)

    def load_version(self, id):
        return self.versions.where(Version.sequential == id).first()

    @property
    def locked_version(self):
        return getattr(self, '_locked_version', None)

    @locked_version.setter
    def locked_version(self, value):
        # Should be set only once, and never updated.
        assert not hasattr(self, '_locked_version'), 'locked_version is read only'  # noqa
        self._locked_version = value

    def lock_version(self):
        if not self.id:
            self.version = 1
        self._locked_version = self.version if self.id else 0

    def increment_version(self):
        self.version = self.version + 1

    def check_version(self):
        if self.version != self.locked_version + 1:
            raise ForcedVersionError('wrong version number: {}'.format(self.version))  # noqa

    def update_meta(self):
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

    def save(self, *args, **kwargs):
        self.check_version()
        self.update_meta()
        super().save(*args, **kwargs)
        self.store_version()
        self.lock_version()


class ResourceQueryResultWrapper(peewee.ModelQueryResultWrapper):

    def process_row(self, row):
        instance = super().process_row(row)
        return instance.as_resource


class SelectQuery(db.SelectQuery):

    @peewee.returns_clone
    def as_resource(self):
        self._result_wrapper = ResourceQueryResultWrapper


class Version(db.Model):
    model = peewee.CharField(max_length=64)
    model_id = peewee.IntegerField()
    sequential = peewee.IntegerField()
    data = peewee.BlobField()

    class Meta:
        manager = SelectQuery

    def __repr__(self):
        return '<Version {} of {}({})>'.format(self.sequential, self.model,
                                               self.model_id)

    @property
    def as_resource(self):
        return pickle.loads(self.data)

    def load(self):
        return BaseVersioned.registry[self.model](**self.as_resource)

    @property
    def diff(self):
        return Diff.first(Diff.new == self.id)


class Diff(db.Model):

    # Allow to skip diff at very first data import.
    ACTIVE = True

    # old is empty at creation.
    old = db.ForeignKeyField(Version, null=True)
    # new is empty after delete.
    new = db.ForeignKeyField(Version, null=True)
    diff = db.BinaryJSONField()
    created_at = db.DateTimeField()

    class Meta:
        validate_backrefs = False
        manager = SelectQuery

    def save(self, *args, **kwargs):
        if not self.diff:
            meta = set(['id', 'created_by', 'modified_by', 'created_at',
                        'modified_at', 'version'])
            old = self.old.as_resource if self.old else {}
            new = self.new.as_resource if self.new else {}
            keys = set(list(old.keys()) + list(new.keys())) - meta
            self.diff = {}
            for key in keys:
                old_value = old.get(key)
                new_value = new.get(key)
                if new_value != old_value:
                    self.diff[key] = {
                        'old': str(old_value),
                        'new': str(new_value)
                    }
        super().save(*args, **kwargs)

    @property
    def as_resource(self):
        version = self.new or self.old
        return {
            'old': self.old.as_resource if self.old else None,
            'new': self.new.as_resource if self.new else None,
            'diff': self.diff,
            'resource': version.model.lower(),
            'id': version.model_id,
            'created_at': self.created_at
        }
