import json
import re

from urllib.parse import urlencode

from django.conf.urls import url
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
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
    identifiers = []
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

    def dispatch(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.key and self.key not in self.identifiers + ['id']:
            return HttpResponseBadRequest(
                                    'Invalid identifier: {}'.format(self.ref))
        if self.request.method == 'GET' and self.path:
            view = getattr(self, self.path, None)
            if view and callable(view):
                return view(*args, **kwargs)
            else:
                return HttpResponseNotFound()
        return super().dispatch(*args, **kwargs)

    @classmethod
    def url_path(cls):
        return cls.base_url() + r'(?:(?P<key>[\w_]+)/(?P<ref>[\w_]+)/(?:(?P<path>[\w_]+)/)?)?$'  # noqa

    def to_json(self, status=200, **kwargs):
        return HttpResponse(json.dumps(kwargs), status=status)

    def get_object(self):
        return self.model.objects.get(**{self.key: self.ref})

    def get(self, *args, **kwargs):
        self.object = self.get_object()
        return self.to_json(**self.object.as_json)

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
                status = 200 if self.ref else 201
            return self.to_json(status=status, **self.object.as_json)
        else:
            return self.to_json(status=422, errors=form.errors)

    def get_limit(self):
        return min(int(self.request.GET.get('limit', self.DEFAULT_LIMIT)),
                   self.MAX_LIMIT)

    def get_offset(self):
        try:
            return int(self.request.GET.get('offset'))
        except (ValueError, TypeError):
            return 0

    def collection(self, queryset):
        limit = self.get_limit()
        offset = self.get_offset()
        end = offset + limit
        count = queryset.count()
        kwargs = {
            'collection': list(queryset[offset:end]),
            'total': count,
        }
        url = '{}://{}{}'.format(self.request.scheme, self.request.get_host(),
                                 self.request.path)
        if count > end:
            kwargs['next'] = '{}?{}'.format(url, urlencode({'offset': end}))
        if offset >= limit:
            kwargs['previous'] = '{}?{}'.format(url, urlencode({'offset': offset - limit}))  # noqa
        return self.to_json(200, **kwargs)


class Position(BaseCRUD):
    model = models.Position
    form_class = forms.Position


class Housenumber(BaseCRUD):
    identifiers = ['cia']
    model = models.HouseNumber
    form_class = forms.HouseNumber

    def positions(self, *args, **kwargs):
        self.object = self.get_object()
        return self.collection(self.object.position_set.as_json)


class Street(BaseCRUD):
    model = models.Street
    form_class = forms.Street
    identifiers = ['fantoir']

    def housenumbers(self, *args, **kwargs):
        self.object = self.get_object()
        return self.collection(self.object.housenumber_set.as_json)


class Municipality(BaseCRUD):
    identifiers = ['siren', 'insee']
    model = models.Municipality
    form_class = forms.Municipality

    def streets(self, *args, **kwargs):
        self.object = self.get_object()
        return self.collection(self.object.street_set.as_json)
