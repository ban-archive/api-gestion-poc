import peewee

from ban import db
from ban.utils import make_diff


class ResourceValidator:
    errors = None

    def __init__(self, model, update=False):
        self.model = model
        self.update = update

    def error(self, key, message):
        # Should we create a list and append insteaad?
        if key not in self.errors:
            self.errors[key] = message

    def validate(self, data, instance=None):
        self.errors = {}
        self.instance = instance
        self.data = {}
        for name, field in self.model._meta.fields.items():
            if (name in self.model.readonly_fields
                 or name not in self.model.resource_fields):
                continue
            if self.update and not name in data and name is not 'version':
                continue
            try:
                self.data[name] = self.validate_field(field, data.get(name))
            except ValueError as e:
                self.error(name, str(e))
                continue

        if hasattr(self.model, 'validate'):
            for key, message in self.model.validate(self, self.data,
                                                    instance).items():
                self.error(key, message)

    def validate_field(self, field, value):
        coerce = getattr(field, 'coerce', None)
        if coerce:
            try:
                value = coerce(value)
            except (ValueError, TypeError):
                raise ValueError('Unable to coerce value "{}"'.format(value))
            except peewee.DoesNotExist:
                raise ValueError('No matching resource for "{}"'.format(value))

        if value and not isinstance(value, field.__data_type__):
            raise ValueError('"{value}" is not of type "{type}".'.format(
                value=value, type=field.__data_type__
            ))
        checks = ['null', 'choices', 'min_length', 'max_length', 'unique']
        for check in checks:
            if getattr(field, check, None) is not None:
                getattr(self, 'validate_{}'.format(check))(field, value)
        return value

    def validate_null(self, field, value):
        if field.__data_type__ == bool and value is not None:
            return

        if not value and not field.null:
            raise ValueError('Value should not be null')

    def validate_choices(self, field, value):
        choices = [choice[0] for choice in field.choices]
        if value and value not in choices:
            raise ValueError('"{}" should be one of the following choices: {}'
                             .format(value, ','.join(choices)))

    def validate_min_length(self, field, value):
        if value and len(value) < field.min_length:
            raise ValueError('"{}" should be minimum {} characters'.format(
                value, field.min_length
            ))

    def validate_max_length(self, field, value):
        if value and len(value) > field.max_length:
            raise ValueError('"{}" should be maximum {} characters'.format(
                value, field.max_length
            ))

    def validate_unique(self, field, value):
        if not value or not field.unique:
            return
        qs = self.model.select().where(field == value)
        if self.instance:
            qs = qs.where(self.model.pk != self.instance.pk)
        if qs.exists():
            raise ValueError('"{}" already exists'.format(value))

    def patch(self):
        for key, value in self.data.items():
            setattr(self.instance, key, value)

    def save(self):
        if self.errors:
            raise ValueError('Invalid document')
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
