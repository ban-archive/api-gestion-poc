import json
import re

from django.conf.urls import url
from django.db.models.signals import class_prepared
from django.dispatch import receiver
from django.http import HttpResponse
from django.views.generic import View

from ban.core import models, forms
from ban.versioning.exceptions import ForcedVersionError


class WithURL(type):

    urls = []

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs)
        if hasattr(cls, 'as_view'):
            mcs.urls.append(url(cls.url_path(), cls.as_view(),
                                name=cls.url_name()))
        return cls


class URLMixin(object, metaclass=WithURL):

    @classmethod
    def base_url(cls):
        return re.sub("([a-z])([A-Z])", "\g<1>/\g<2>",
                      cls.__name__).lower() + "/"

    @classmethod
    def url_name(cls):
        return re.sub("([a-z])([A-Z])", "\g<1>-\g<2>", cls.__name__).lower()

    @classmethod
    def url_path(cls):
        return cls.base_url()


class BaseCRUD(URLMixin, View):

    def dispatch(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return super().dispatch(*args, **kwargs)

    @classmethod
    def url_path(cls):
        return cls.base_url() + r'(?:(?P<ref>[\w_]+)/)?$'

    def to_json(self, status=200, **kwargs):
        return HttpResponse(json.dumps(kwargs), status=status)

    def get_object(self):
        return self.model.objects.get(pk=self.ref)

    def get(self, *args, **kwargs):
        self.object = self.get_object()
        return self.to_json(**self.object.public_data)

    def post(self, *args, **kwargs):
        if self.ref:
            self.object = self.get_object()
            instance = self.object
        else:
            instance = None
        return self.save_object(self.request.POST, instance)

    def put(self, *args, **kwargs):
        self.object = self.get_object()
        data = json.loads(self.request.body.decode())
        return self.save_object(data, self.object)

    def save_object(self, data, instance=None):
        form = self.form_class(data, instance=instance)
        if form.is_valid():
            try:
                self.object = form.save()
            except ForcedVersionError:
                status = 409
                self.object = self.get_object()
            else:
                status = 200
            return self.to_json(status=status, **self.object.public_data)
        else:
            return self.to_json(status=422, errors=form.errors)


class Position(BaseCRUD):
    model = models.Position
    form_class = forms.Position


class Housenumber(BaseCRUD):
    model = models.HouseNumber
    form_class = forms.HouseNumber

    def get_object(self):
        return self.model.from_ref(self.ref)


class Street(BaseCRUD):
    model = models.Street
    form_class = forms.Street

    def get_object(self):
        return self.model.from_ref(self.ref)


@receiver(class_prepared)
def register_searchable_model(sender, **kwargs):
    if issubclass(sender, URLMixin):
        URLMixin.urls.append(url(sender.url_path(), sender.as_view(),
                             name=sender.url_name()))
