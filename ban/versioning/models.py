import pickle

from django.db import models
from django.db.models.signals import (class_prepared, post_init, post_save,
                                      pre_save)
from django.dispatch import receiver
from django.forms.models import model_to_dict

from .exceptions import ForcedVersionError


class VersionMixin(models.Model):

    version = models.SmallIntegerField(default=1)

    class Meta:
        abstract = True
        unique_together = ('pk', 'version')

    def serialize(self):
        data = model_to_dict(self)
        # Store relations ids, not instances.
        fields = self._meta.get_fields()
        for field in fields:
            if field.name in data and field.is_relation:
                data[field.attname] = data[field.name]
                del data[field.name]
        return pickle.dumps(data)

    def store_version(self):
        Version.objects.create(
            model=self.__class__.__name__,
            model_id=self.pk,
            sequential=self.version,
            data=self.serialize()
        )

    @property
    def versions(self):
        return Version.objects.filter(model=self.__class__.__name__,
                                      model_id=self.pk)

    @property
    def locked_version(self):
        return getattr(self, '_locked_version', None)

    @locked_version.setter
    def locked_version(self, value):
        # Should be set only once, and never updated.
        assert not hasattr(self, '_locked_version'), 'locked_version is read only'  # noqa
        self._locked_version = value

    def lock_version(self):
        self._locked_version = self.version if self.pk else 0

    def increment_version(self):
        self.version = self.version + 1


class Version(models.Model):
    model = models.CharField(max_length=64)
    model_id = models.IntegerField()
    sequential = models.SmallIntegerField()
    data = models.BinaryField()

    def as_dict(self):
        return pickle.loads(self.data)

    def load(self):
        return VERSIONED[self.model](**self.as_dict())


@receiver(post_save)
def store_version(sender, instance, **kwargs):
    if VersionMixin in sender.__mro__:
        instance.store_version()
        instance.lock_version()


@receiver(post_init)
def lock_version(sender, instance, **kwargs):
    if VersionMixin in sender.__mro__:
        instance.lock_version()


@receiver(pre_save)
def check_version(sender, instance, **kwargs):
    if VersionMixin in sender.__mro__:
        if not instance.pk:
            instance.version = 1
        if instance.version != instance.locked_version + 1:
            raise ForcedVersionError(
                'wrong version number: {}'.format(instance.version))


@receiver(class_prepared)
def register_versioned_model(sender, **kwargs):
    if issubclass(sender, VersionMixin):
        VERSIONED[sender.__name__] = sender
VERSIONED = {}
