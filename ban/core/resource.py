import peewee
from cerberus import ValidationError, Validator

from ban import db


class ResourceValidator(Validator):

    ValidationError = ValidationError

    def __init__(self, model, *args, **kwargs):
        self.model = model
        super().__init__(model._meta.resource_schema, *args, **kwargs)

    def _validate_type_point(self, field, value):
        if not isinstance(value, (str, list, tuple)):
            self._error(field, 'Invalid Point: {}'.format(value))

    def save(self, instance=None):
        if self.errors:
            raise ValidationError('Invalid document')
        if instance:
            for key, value in self.document.items():
                setattr(instance, key, value)
            instance.save()
        else:
            instance = self.model.create(**self.document)
        return instance


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


class BaseResource(peewee.BaseModel):

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs, **kwargs)
        cls._meta.resource_schema = cls.build_resource_schema()
        return cls


class ResourceModel(db.Model, metaclass=BaseResource):
    resource_fields = []

    class Meta:
        abstract = True
        resource_schema = {}

    @classmethod
    def build_resource_schema(cls):
        schema = {}
        for field in cls._meta.get_fields():
            if field.name not in cls.get_resource_fields():
                continue
            if field.primary_key:
                continue
            type_ = getattr(field.__class__, 'schema_type', None)
            if not type_:
                continue
            row = {
                'type': type_,
                'required': not field.null,
                'coerce': field.coerce,
            }
            max_length = getattr(field, 'max_length', None)
            if max_length:
                row['maxlength'] = max_length
            if not field.null:
                row['empty'] = False
            row.update(cls._meta.resource_schema.get(field.name, {}))
            schema[field.name] = row
        return schema

    @classmethod
    def validator(cls, instance=None, **data):
        validator = ResourceValidator(cls, instance)
        validator(data)
        return validator

    # TODO find a way not to override the peewee.Model select classmethod.
    @classmethod
    def select(cls, *selection):
        query = SelectQuery(cls, *selection)
        if cls._meta.order_by:
            query = query.order_by(*cls._meta.order_by)
        return query

    @classmethod
    def where(cls, *args, **kwargs):
        """Shortcut for select().where()"""
        return cls.select().where(*args, **kwargs)

    @classmethod
    def first(cls, *args, **kwargs):
        """Shortcut for select().where().first()"""
        return cls.where(*args, **kwargs).first()

    @classmethod
    def get_resource_fields(self):
        return self.resource_fields + ['id', 'version']

    @property
    def as_resource(self):
        return {f: self.as_resource_field(f) for f in self.get_resource_fields()}

    @property
    def as_relation(self):
        return {f: self.as_relation_field(f) for f in self.get_resource_fields()}

    def as_resource_field(self, name):
        value = getattr(self, '{}_json'.format(name), getattr(self, name))
        return getattr(value, 'as_relation', value)

    def as_relation_field(self, name):
        value = getattr(self, name)
        return getattr(value, 'id', value)
