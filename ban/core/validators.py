from copy import deepcopy

import peewee
from jsonschema import Draft4Validator, ValidationError, FormatChecker
from jsonschema import validators
from postgis import Point

from ban import db
from ban.utils import make_diff


extra_types = {
    'point': Point,
    'foreignkey': int,
}


def validate_unique(validator, value, instance, schema):
    # "instance" is the current field value.
    # "value" is the value of "unique" in the schema
    model = schema['model']
    field = schema['field']
    if field.name in validator.errors:
        # Value has not been coerced? Does not try to run a SQL with it.
        return []
    qs = model.select()
    qs = qs.where(field == instance)
    if validator.instance:
        qs = qs.where(model.pk != validator.instance.pk)
    if qs.exists():
        return [ValidationError("'{}': Duplicate value: {}".format(field.name,
                                                                   instance))]
    return []


Validator = validators.extend(Draft4Validator, {
    'unique': validate_unique
})


class ResourceValidator(Validator):
    ValidationError = ValidationError
    errors = None

    def __init__(self, model, update=False):
        self.model = model
        self.update = update
        self.schema = self.prepare()
        super().__init__(self.schema, types=extra_types,
                         format_checker=FormatChecker())

    def prepare(self):
        jsonschema = deepcopy(self.model.jsonschema)
        properties = {}
        for attr, schema in self.model.jsonschema['properties'].items():
            # TODO PR against python-jsonschema to deal with readOnly.
            if schema.get('readOnly'):
                continue
            properties[attr] = schema
        jsonschema['properties'] = properties
        return jsonschema

    def error(self, key, message):
        # Should we create a list and append insteaad?
        if key not in self.errors:
            self.errors[key] = message

    def validate(self, data, instance=None):
        self.errors = {}
        self.instance = instance
        self.data = self.coerce(data)
        for error in self.iter_errors(self.data):
            # Draft4Validator does not provide any reliable endpoint to get the
            # failed property. Worse, in the case of "required" check, the
            # failed property does not appear at all but in the message.
            if error.validator == 'required':
                key = error.message.split("'")[1]
            else:
                key = error.relative_path[0]
            self.error(key, error.message)
        if hasattr(self.model, 'validate'):
            for key, message in self.model.validate(self, self.data,
                                                    instance).items():
                self.error(key, message)

    def coerce(self, data):
        for attr, value in data.items():
            field = getattr(self.model, attr, None)
            if not field:
                continue  # Unknown field passed in data, ignore.
            func = getattr(field, 'coerce', None)
            if not func:
                continue
            try:
                data[attr] = func(value)
            except (ValueError, TypeError):
                self.error(attr, ('Unable to coerce value {} '
                                  'for field {}'.format(value, attr)))
            except peewee.DoesNotExist:
                self.error(attr, 'No matching resource for {}'.format(value))
        return data

    def patch(self):
        for key, value in self.data.items():
            setattr(self.instance, key, value)

    def save(self):
        if self.errors:
            raise ValidationError('Invalid document')
        database = self.model._meta.database
        if self.instance:
            with database.atomic():
                self.patch()
                self.instance.save()
        else:
            with database.atomic():
                m2m = {}
                data = {}
                for key, value in self.data.items():
                    field = getattr(self.model, key)
                    if isinstance(field, db.ManyToManyField):
                        m2m[key] = value
                    else:
                        data[key] = value
                self.instance = self.model.create(**data)
                # m2m need the instance to be saved.
                for key, value in m2m.items():
                    setattr(self.instance, key, value)
        return self.instance


class VersionedResourceValidator(ResourceValidator):

    def prepare(self):
        jsonschema = super().prepare()
        if self.update:
            # Means we are updating the model, so no need for checking the
            # required fields.
            jsonschema['required'] = ['version']
        return jsonschema

    def validate(self, data, instance=None):
        if not instance:
            # Be smart, no need to make the field mandatory at creation time.
            data['version'] = 1
        return super().validate(data, instance)

    def patch(self):
        # Let's try to be smart and patch object if claimed version does not
        # match with expected but not conflict is detected.
        claimed_version = max(1, self.data.get('version', 1))
        current_version = self.instance.version if self.instance else 0
        if self.instance and claimed_version <= current_version > 1:
            base = self.instance.load_version(claimed_version - 1)
            current = self.instance.load_version(current_version)
            diff = make_diff(base.data, current.data)
            # Those are keys changed between that last know version of the
            # client and the current version we have.
            protected = diff.keys()
            diff = make_diff(base.data, self.data,
                             update=self.update)
            conflict = any(k in protected for k in diff.keys())
            if not conflict:
                for key in diff.keys():
                    setattr(self.instance, key, self.data.get(key))
                self.instance.increment_version()
                return
        super().patch()
