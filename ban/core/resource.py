import peewee
from cerberus import ValidationError, Validator, errors

from ban import db
from postgis import Point


class ResourceValidator(Validator):

    ValidationError = ValidationError

    def __init__(self, model, *args, **kwargs):
        self.model = model
        kwargs['purge_unknown'] = True
        super().__init__(model._meta.resource_schema, *args, **kwargs)

    def _validate_type_point(self, field, value):
        if not isinstance(value, (str, list, tuple, Point)):
            self._error(field, 'Invalid Point: {}'.format(value))

    def _validate_coerce(self, coerce, field, value):
        # See https://github.com/nicolaiarocci/cerberus/issues/171.
        try:
            value = coerce(value)
        except (TypeError, ValueError, peewee.DoesNotExist):
            self._error(field, errors.ERROR_COERCION_FAILED.format(field))
        return value

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


class ResourceListQueryResultWrapper(peewee.ModelQueryResultWrapper):

    def process_row(self, row):
        instance = super().process_row(row)
        return instance.as_list


class SelectQuery(db.SelectQuery):

    @peewee.returns_clone
    def as_resource(self):
        self._result_wrapper = ResourceQueryResultWrapper

    @peewee.returns_clone
    def as_resource_list(self):
        self._result_wrapper = ResourceListQueryResultWrapper


class BaseResource(peewee.BaseModel):

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs, **kwargs)
        cls._meta.resource_schema = cls.build_resource_schema()
        return cls


class ResourceModel(db.Model, metaclass=BaseResource):
    resource_fields = []
    identifiers = []

    class Meta:
        abstract = True
        resource_schema = {}
        manager = SelectQuery

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
    def validator(cls, instance=None, update=False, **data):
        validator = ResourceValidator(cls, instance)
        validator(data, update=update)
        return validator

    @classmethod
    def get_resource_fields(cls):
        return cls.resource_fields + ['id']

    @classmethod
    def get_list_fields(cls):
        return cls.get_resource_fields() + ['resource']

    @property
    def resource(self):
        return self.__class__.__name__.lower()

    @property
    def as_resource(self):
        return {f: self.as_resource_field(f)
                for f in self.get_resource_fields()}

    @property
    def as_list(self):
        return {f: self.as_list_field(f) for f in self.get_list_fields()}

    @property
    def as_relation(self):
        return {f: self.as_relation_field(f)
                for f in self.get_resource_fields()}

    def as_resource_field(self, name):
        value = getattr(self, '{}_resource'.format(name), getattr(self, name))
        return getattr(value, 'as_relation', value)

    def as_relation_field(self, name):
        value = getattr(self, name)
        return getattr(value, 'id', value)

    def as_list_field(self, name):
        value = getattr(self, '{}_resource'.format(name), getattr(self, name))
        return getattr(value, 'id', value)

    @classmethod
    def coerce(cls, id, identifier=None):
        if not identifier:
            identifier = 'id'
            if isinstance(id, str):
                *extra, id = id.split(':')
                if extra:
                    identifier = extra[0]
                if identifier not in cls.identifiers + ['id']:
                    raise cls.DoesNotExist("Invalid identifier {}".format(
                                                                identifier))
        try:
            return cls.get(getattr(cls, identifier) == id)
        except cls.DoesNotExist:
            # Is it an old identifier?
            from .versioning import IdentifierRedirect
            new = IdentifierRedirect.follow(cls, identifier, id)
            if new:
                return cls.get(getattr(cls, identifier) == new)
            else:
                raise
