from django.db import models


class VersionField(models.SmallIntegerField):

    def __init__(self, *args, **kwargs):
        kwargs['default'] = 0
        kwargs['editable'] = False
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        value = value + 1
        setattr(model_instance, self.attname, value)
        return value
