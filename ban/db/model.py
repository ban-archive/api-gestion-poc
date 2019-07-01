import peewee

from .connections import database
from . import cache


class SerializerModelObjectCursorWrapper(peewee.ModelObjectCursorWrapper):
    def process_row(self, row):
        instance = super().process_row(row)
        if hasattr(self, '_serializer'):
            instance = self._serializer(instance)
        return instance


class ModelSelect(peewee.ModelSelect):

    @peewee.database_required
    def execute(self, database):
        wrapper = super()._execute(database)
        if hasattr(self, '_serializer'):
            wrapper._serializer = self._serializer
        return wrapper

    @peewee.Node.copy
    def serialize(self, mask=None):
        self._serializer = lambda inst: inst.serialize(mask)
        self._result_wrapper = SerializerModelObjectCursorWrapper

    def _get_model_cursor_wrapper(self, cursor):
        wrapper = getattr(self, '_result_wrapper', None)
        if wrapper is not None:
            return wrapper(cursor, self.model, [], self.model)
        else:
            return super()._get_model_cursor_wrapper(cursor)


class Model(peewee.Model):

    # id is reserved for BAN external id, but lets be consistent and use the
    # same primary key name all over the models.
    pk = peewee.AutoField()

    class Meta:
        database = database
        manager = ModelSelect

    def save(self, *args, **kwargs):
        cache.clear()
        super().save(*args, **kwargs)

    @classmethod
    def select(cls, *fields):
        is_default = not fields
        if not fields:
            fields = cls._meta.sorted_fields
        query = cls._meta.manager(cls, fields, is_default=is_default)
        if hasattr(cls._meta, 'order_by'):
            order_by_list = [getattr(cls, o) for o in cls._meta.order_by]
            query = query.order_by(order_by_list)
        return query

    @classmethod
    def where(cls, *expressions):
        """Shortcut for select().where()"""
        return cls.select().where(*expressions)

    @classmethod
    def first(cls, *expressions):
        """Shortcut for select().where().first()"""
        qs = cls.select()
        if expressions:
            qs = qs.where(*expressions)
        # See https://github.com/coleifer/peewee/commit/eeb6d4d727da8536906a00c490f94352465e90bb  # noqa
        return qs.limit(1).first()

    def __setattr__(self, name, value):
        attr = getattr(self.__class__, name, None)
        if attr and hasattr(attr, 'adapt'):
            value = attr.adapt(value)
        return super().__setattr__(name, value)
