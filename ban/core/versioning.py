from datetime import datetime
import json

import decorator
import peewee

from ban import db
from ban.auth.models import Client, Session
from ban.core.encoder import dumps
from ban.utils import make_diff, utcnow

from . import context


@decorator.decorator
def flag_id_required(func, self, *args, **kwargs):
    session = context.get('session')
    if not session:
        raise ValueError('Must be logged in.')
    if not session.client:
        raise ValueError('Token must be linked to a client.')
    if not session.client.flag_id:
        raise ValueError('Client must have a valid flag_id.')

    # Even if session is declared as kwarg, "decorator" helper injects it
    # as arg. Bad.
    args = list(args)
    args[0] = session
    func(self, *args, **kwargs)


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
        validate_backrefs = False
        unique_together = ('pk', 'version')

    def prepared(self):
        self.lock_version()
        super().prepared()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prepared()

    def store_version(self):
        new = Version.create(
            model_name=self.__class__.__name__,
            model_pk=self.pk,
            sequential=self.version,
            data=self.as_version,
            period=[self.modified_at, None]
        )
        old = None
        if self.version > 1:
            old = self.load_version(self.version - 1)
            old.close_period(new.period.lower)
        if Diff.ACTIVE:
            Diff.create(old=old, new=new, created_at=self.modified_at)

    @property
    def versions(self):
        return Version.select().where(
            Version.model_name == self.__class__.__name__,
            Version.model_pk == self.pk).order_by(Version.sequential)

    def load_version(self, ref=None):
        qs = self.versions
        if ref is None:
            ref = self.version
        if isinstance(ref, datetime):
            qs = qs.where(Version.period.contains(ref))
        else:
            qs = qs.where(Version.sequential == ref)
        return qs.first()

    @property
    def locked_version(self):
        return getattr(self, '_locked_version', None)

    @locked_version.setter
    def locked_version(self, value):
        # Should be set only once, and never updated.
        assert not hasattr(self, '_locked_version'), 'locked_version is read only'  # noqa
        self._locked_version = value

    def lock_version(self):
        if not self.pk:
            self.version = 1
        self._locked_version = self.version if self.pk else 0

    def increment_version(self):
        self.version = self.version + 1

    def check_version(self):
        if self.version != self.locked_version + 1:
            raise ForcedVersionError('wrong version number: {}'.format(self.version))  # noqa

    def update_meta(self):
        session = context.get('session')
        if session:  # TODO remove this if, session should be mandatory.
            try:
                getattr(self, 'created_by', None)
            except Session.DoesNotExist:
                # Field is not nullable, we can't access it when it's not yet
                # defined.
                self.created_by = session
            self.modified_by = session
        now = utcnow()
        if not self.created_at:
            self.created_at = now
        self.modified_at = now

    def save(self, *args, **kwargs):
        with self._meta.database.atomic():
            self.check_version()
            self.update_meta()
            super().save(*args, **kwargs)
            self.store_version()
            self.lock_version()


class SelectQuery(db.SelectQuery):

    @peewee.returns_clone
    def serialize(self):
        self._serializer = lambda inst: inst.serialize()
        super().serialize()


class Version(db.Model):

    __openapi__ = """
        properties:
            data:
                type: object
                description: serialized resource
            flag:
                type: array
                items:
                    $ref: '#/definitions/Flag'
        """

    model_name = db.CharField(max_length=64)
    model_pk = db.IntegerField()
    sequential = db.IntegerField()
    data = db.BinaryJSONField()
    period = db.DateRangeField()

    class Meta:
        manager = SelectQuery
        indexes = (
            (('model_name', 'model_pk', 'sequential'), True),
        )

    def __repr__(self):
        return '<Version {} of {}({})>'.format(self.sequential,
                                               self.model_name, self.model_pk)

    def serialize(self, *args):
        return {
            'data': self.data,
            'flags': list(self.flags.serialize())
        }

    @property
    def model(self):
        return BaseVersioned.registry[self.model_name]

    def load(self):
        validator = self.model.validator(**self.data)
        return self.model(**validator.data)

    @property
    def diff(self):
        return Diff.first(Diff.new == self.pk)

    @flag_id_required
    def flag(self, session=None):
        """Flag current version with current client."""
        if not Flag.where(Flag.version == self,
                          Flag.client == session.client).exists():
            Flag.create(version=self, session=session, client=session.client)

    @flag_id_required
    def unflag(self, session=None):
        """Delete current version's flags made by current session client."""
        Flag.delete().where(Flag.version == self,
                            Flag.client == session.client).execute()

    def close_period(self, bound):
        # DateTimeRange is immutable, so create new one.
        self.period = [self.period.lower, bound]
        self.save()


class Diff(db.Model):

    __openapi__ = """
        properties:
            resource:
                type: string
                description: name of the resource the diff is applied to
            resource_id:
                type: string
                description: id of the resource the diff is applied to
            created_at:
                type: string
                format: date-time
                description: the date and time the diff has been created at
            old:
                type: object
                description: the resource before the change
            new:
                type: object
                description: the resource after the change
            diff:
                type: object
                description: detail of changed properties
            """

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
        order_by = ('pk', )

    def save(self, *args, **kwargs):
        if not self.diff:
            old = self.old.data if self.old else {}
            new = self.new.data if self.new else {}
            self.diff = make_diff(old, new)
        super().save(*args, **kwargs)
        IdentifierRedirect.from_diff(self)

    def serialize(self, *args):
        version = self.new or self.old
        return {
            'increment': self.pk,
            'old': self.old.data if self.old else None,
            'new': self.new.data if self.new else None,
            'diff': self.diff,
            'resource': version.model_name.lower(),
            'resource_pk': version.model_pk,
            'created_at': self.created_at
        }


class IdentifierRedirect(db.Model):
    model_name = db.CharField(max_length=64)
    identifier = db.CharField(max_length=64)
    old = db.CharField(max_length=255)
    new = db.CharField(max_length=255)

    @classmethod
    def from_diff(cls, diff):
        if not diff.new or not diff.old:
            # Only update makes sense for us, no creation nor deletion.
            return
        model = diff.new.model
        identifiers = [i for i in model.identifiers if i in diff.diff]
        for identifier in identifiers:
            old = diff.diff[identifier]['old']
            new = diff.diff[identifier]['new']
            if not old or not new:
                continue
            cls.get_or_create(model_name=diff.new.model_name,
                              identifier=identifier, old=old, new=new)
            cls.refresh(model, identifier, old, new)

    @classmethod
    def follow(cls, model, identifier, old):
        row = cls.select().where(cls.model_name == model.__name__,
                                 cls.identifier == identifier,
                                 cls.old == old).first()
        return row.new if row else None

    @classmethod
    def refresh(cls, model, identifier, old, new):
        """An identifier was a target and it becomes itself a target."""
        cls.update(new=new).where(cls.new == old,
                                  cls.model_name == model.__name__,
                                  cls.identifier == identifier).execute()


class Flag(db.Model):

    __openapi__ = """
        properties:
            at:
                type: string
                format: date-time
                description: when the flag has been created
            by:
                type: string
                description: identifier of the client who flagged the version
        """

    version = db.ForeignKeyField(Version, related_name='flags')
    client = db.ForeignKeyField(Client)
    session = db.ForeignKeyField(Session)
    created_at = db.DateTimeField()

    class Meta:
        manager = SelectQuery

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = utcnow()
        super().save(*args, **kwargs)

    def serialize(self, *args):
        return {
            'at': self.created_at,
            'by': self.client.flag_id
        }
