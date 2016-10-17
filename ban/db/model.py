import peewee

from .connections import default


class SerializerQueryResultWrapper(peewee.ModelQueryResultWrapper):

    def process_row(self, row):
        instance = super().process_row(row)
        if hasattr(self, '_serializer'):
            instance = self._serializer(instance)
        return instance


class SelectQuery(peewee.SelectQuery):

    def execute(self):
        wrapper = super().execute()
        if hasattr(self, '_serializer'):
            wrapper._serializer = self._serializer
        return wrapper

    @peewee.returns_clone
    def serialize(self, mask=None):
        self._serializer = lambda inst: inst.serialize(mask)
        self._result_wrapper = SerializerQueryResultWrapper

    def _get_result_wrapper(self):
        wrapper = getattr(self, '_result_wrapper', None)
        if wrapper:
            return wrapper
        return super()._get_result_wrapper()

    def __len__(self):
        return self.count()

    def __getitem__(self, value):
        if isinstance(value, slice):
            # When doing a slice, Peewee execute the whole query and do a slice
            # on the result, which obviously is suboptimal.
            self._offset = value.start
            self._limit = value.stop - value.start
            value = slice(0, None)
        return super().__getitem__(value)


class Model(peewee.Model):

    # id is reserved for BAN external id, but lets be consistent and use the
    # same primary key name all over the models.
    pk = peewee.PrimaryKeyField()

    class Meta:
        database = default
        manager = SelectQuery

    # TODO find a way not to override the peewee.Model select classmethod.
    @classmethod
    def select(cls, *selection):
        query = cls._meta.manager(cls, *selection)
        if cls._meta.order_by:
            query = query.order_by(*cls._meta.order_by)
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
        if attr and hasattr(attr, 'coerce'):
            value = attr.coerce(value)
        return super().__setattr__(name, value)
