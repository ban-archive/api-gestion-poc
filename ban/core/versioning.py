import pickle

import peewee

from ban import db


class ForcedVersionError(Exception):
    pass


class BaseVersioned(peewee.BaseModel):

    registry = {}

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs, **kwargs)
        BaseVersioned.registry[name] = cls
        return cls


class Versioned(peewee.Model, metaclass=BaseVersioned):

    ForcedVersionError = ForcedVersionError

    version = db.IntegerField(default=1)

    class Meta:
        abstract = True
        unique_together = ('id', 'version')

    @classmethod
    def get(cls, *query, **kwargs):
        instance = super().get(*query, **kwargs)
        instance.lock_version()
        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_version()

    def serialize(self):
        data = {}
        for field in self._meta.get_fields():
            value = getattr(self, field.name)
            if isinstance(value, peewee.Model):
                value = value.id
            data[field.name] = value
        return pickle.dumps(data)

    def store_version(self):
        Version.create(
            model=self.__class__.__name__,
            model_id=self.id,
            sequential=self.version,
            data=self.serialize()
        )

    @property
    def versions(self):
        return Version.select().where(Version.model == self.__class__.__name__,
                                      Version.model_id == self.id)

    def load_version(self, id):
        return self.versions.filter(Version.sequential == id).first()

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

    def save(self, *args, **kwargs):
        self.check_version()
        super().save(*args, **kwargs)
        self.store_version()
        self.lock_version()


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


class Version(peewee.Model):
    model = peewee.CharField(max_length=64)
    model_id = peewee.IntegerField()
    sequential = peewee.IntegerField()
    data = peewee.BlobField()

    class Meta:
        database = db.default

    # TODO find a way not to override the peewee.Model select classmethod.
    @classmethod
    def select(cls, *selection):
        query = SelectQuery(cls, *selection)
        if cls._meta.order_by:
            query = query.order_by(*cls._meta.order_by)
        return query

    @property
    def as_resource(self):
        return pickle.loads(self.data)

    def load(self):
        return BaseVersioned.registry[self.model](**self.as_resource)
