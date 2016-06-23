from cerberus import ValidationError, Validator, errors
import peewee
from postgis import Point

from ban import db
from ban.utils import make_diff


class ResourceValidator(Validator):

    ValidationError = ValidationError
    ERROR_REQUIRED_FIELD = errors.ERROR_REQUIRED_FIELD

    def __init__(self, model, *args, **kwargs):
        self.model = model
        kwargs['purge_unknown'] = True
        super().__init__(model.resource_schema, *args, **kwargs)

    def _validate_type_point(self, field, value):
        if not isinstance(value, (str, list, tuple, Point)):
            self._error(field, 'Invalid Point: {}'.format(value))

    def _validate_type_foreignkey(self, field, value):
        if not isinstance(value, int):
            self._error(field, 'No matching resource for {}'.format(value))

    def _validate_unique(self, unique, field, value):
        qs = self.model.select()
        attr = getattr(self.model, field)
        qs = qs.where(attr == value)
        if self.instance:
            qs = qs.where(self.model.pk != self.instance.pk)
        if qs.exists():
            self._error(field, 'Duplicate value for {}: {}'.format(field,
                                                                   value))

    def _validate_coerce(self, coerce, field, value):
        # See https://github.com/nicolaiarocci/cerberus/issues/171.
        try:
            value = coerce(value)
        except (TypeError, ValueError):
            msg = 'Unable to coerce {} for field {}'
            self._error(field, msg.format(value, field))
        except peewee.DoesNotExist:
            # Error will be handled by _validate_type_foreignkey.
            pass
        return value

    def _purge_readonly(self, data):
        # cf https://github.com/nicolaiarocci/cerberus/issues/240.
        for key in tuple(data):
            if self.schema.get(key, {}).get('readonly'):
                del data[key]

    def validate(self, data, instance=None, **kwargs):
        self.instance = instance
        self._purge_readonly(data)
        super().validate(data, **kwargs)
        if hasattr(self.model, 'validate'):
            for key, message in self.model.validate(self, self.document,
                                                    instance).items():
                self._error(key, message)

    def patch(self):
        for key, value in self.document.items():
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
                for key, value in self.document.items():
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

    def patch(self):
        # Let's try to be smart and patch object if claimed version does not
        # match with expected but not conflict is detected.
        claimed_version = max(1, self.document.get('version', 1))
        current_version = self.instance.version if self.instance else 0
        if self.instance and claimed_version <= current_version > 1:
            base = self.instance.load_version(claimed_version - 1)
            current = self.instance.load_version(current_version)
            diff = make_diff(base.as_resource, current.as_resource)
            # Those are keys changed between that last know version of the
            # client and the current version we have.
            protected = diff.keys()
            diff = make_diff(base.as_resource, self.document,
                             update=self.update)
            conflict = any(k in protected for k in diff.keys())
            if not conflict:
                for key in diff.keys():
                    setattr(self.instance, key, self.document.get(key))
                self.instance.increment_version()
                return
        super().patch()
