import peewee

from .connections import default


class SelectQuery(peewee.SelectQuery):

    def _get_result_wrapper(self):
        return getattr(self, '_result_wrapper', None) \
                                            or super()._get_result_wrapper()

    def __len__(self):
        return self.count()


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
