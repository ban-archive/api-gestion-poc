from copy import deepcopy
import uuid

import peewee

from ban import db

from .validators import ResourceValidator


class SelectQuery(db.SelectQuery):

    @peewee.returns_clone
    def serialize(self, mask=None):
        self._serializer = lambda inst: inst.serialize(mask)
        super().serialize()


class BaseResource(peewee.BaseModel):

    def include_field_for_collection(cls, name):
        if name in cls.exclude_for_collection:
            return False
        attr = getattr(cls, name, None)
        exclude = (db.ManyToManyField, peewee.ReverseRelationDescriptor,
                   peewee.SelectQuery)
        if not attr or isinstance(attr, exclude):
            return False
        return True

    def __new__(mcs, name, bases, attrs, **kwargs):
        # Inherit and extend instead of replacing.
        resource_fields = attrs.pop('resource_fields', None)
        jsonschema = attrs.pop('jsonschema', None)
        exclude_for_collection = attrs.pop('exclude_for_collection', None)
        exclude_for_version = attrs.pop('exclude_for_version', None)
        cls = super().__new__(mcs, name, bases, attrs, **kwargs)
        if resource_fields is not None:
            inherited = getattr(cls, 'resource_fields', {})
            resource_fields.extend(inherited)
            cls.resource_fields = resource_fields
        if jsonschema is not None:
            inherited = getattr(cls, 'jsonschema', {})
            jsonschema['properties'].update(inherited.get('properties', {}))
            cls.jsonschema = jsonschema
        if exclude_for_collection is not None:
            inherited = getattr(cls, 'exclude_for_collection', [])
            exclude_for_collection.extend(inherited)
            cls.exclude_for_collection = exclude_for_collection
        if exclude_for_version is not None:
            inherited = getattr(cls, 'exclude_for_version', [])
            exclude_for_version.extend(inherited)
            cls.exclude_for_version = exclude_for_version
        cls.collection_fields = [
            n for n in cls.resource_fields
            if mcs.include_field_for_collection(cls, n)] + ['resource']
        cls.versioned_fields = [
            n for n in cls.resource_fields
            if n not in cls.exclude_for_version]
        cls.build_jsonschema()
        return cls


class ResourceModel(db.Model, metaclass=BaseResource):
    resource_fields = ['id']
    identifiers = []
    jsonschema = {'type': 'object', 'properties': {'id': {'readOnly': True}},
                  'required': []}
    readonly_fields = ['id', 'pk']
    exclude_for_collection = []
    exclude_for_version = []

    id = db.CharField(max_length=50, unique=True, null=False)

    class Meta:
        manager = SelectQuery
        validator = ResourceValidator

    @classmethod
    def make_id(cls):
        return 'ban-{}-{}'.format(cls.__name__.lower(), uuid.uuid4().hex)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = self.make_id()
        return super().save(*args, **kwargs)

    @classmethod
    def build_jsonschema(cls):
        """Map Peewee models to jsonschema validation."""
        schema = deepcopy(cls.jsonschema)  # Do not share with others.
        schema.setdefault('required', [])
        for name, field in cls._meta.fields.items():
            if name not in cls.resource_fields:
                continue
            if field.primary_key:
                continue
            type_ = getattr(field.__class__, 'schema_type', None)
            if not type_:
                continue
            row = {
                'type': [type_],
                'field': field,
                'model': cls,
            }
            if hasattr(field.__class__, 'schema_format'):
                row['format'] = field.__class__.schema_format
            if field.null:
                row['type'].append('null')
            if field.unique:
                row['unique'] = True
            max_length = getattr(field, 'max_length', None)
            if max_length:
                row['maxLength'] = max_length
            min_length = getattr(field, 'min_length', None)
            if not min_length and type_ == 'string' and not field.null:
                min_length = 1
            if min_length:
                row['minLength'] = min_length
            if getattr(field, 'choices', None):
                row['enum'] = [v for v, l in field.choices]
            row.update(schema['properties'].get(name, {}))  # Inherit values.
            schema['properties'][name] = row
            readonly = row.get('readOnly')
            if (not field.null and name not in schema['required']
               and not readonly):
                schema['required'].append(name)
        cls.jsonschema = schema

    @classmethod
    def validator(cls, instance=None, update=False, **data):
        validator = cls._meta.validator(cls, update=update)
        validator.validate(data, instance=instance)
        return validator

    @property
    def resource(self):
        return self.__class__.__name__.lower()

    @property
    def serialized(self):
        return self.id

    def serialize(self, mask=None):
        if not mask:
            return self.serialized
        dest = {}
        for name, subfields in mask.items():
            if name == '*':
                return self.serialize({k: subfields
                                       for k in self.resource_fields})
            field = getattr(self.__class__, name, None)
            if not field:
                raise ValueError('Unknown field {}'.format(name))
            value = getattr(self, name)
            if value is not None:
                if isinstance(field, (db.ManyToManyField,
                                      peewee.ReverseRelationDescriptor)):
                    value = [v.serialize(subfields) for v in value]
                elif isinstance(field, db.ForeignKeyField):
                    value = value.serialize(subfields)
                elif isinstance(field, db.PointField):
                    value = value.geojson
            dest[name] = value
        return dest

    @property
    def as_resource(self):
        """Resource plus relations."""
        # All fields and all first level relations fields.
        return self.serialize({'*': {}})

    @property
    def as_relation(self):
        """Resources plus relation references without metadata."""
        # All fields plus relations references.
        return self.serialize({f: {} for f in self.collection_fields})

    @property
    def as_version(self):
        """Resources plus relations references and metadata."""
        return self.serialize({f: {} for f in self.versioned_fields})

    @classmethod
    def coerce(cls, id, identifier=None):
        if not identifier:
            identifier = 'id'  # BAN id by default.
            if isinstance(id, str):
                *extra, id = id.split(':')
                if extra:
                    identifier = extra[0]
                if identifier not in cls.identifiers + ['id', 'pk']:
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
