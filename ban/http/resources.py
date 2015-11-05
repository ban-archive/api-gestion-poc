import re
from functools import wraps
from urllib.parse import urlencode

import falcon

from ban.core import models

from .wsgi import app


__all__ = ['Municipality', 'Street', 'Locality', 'Housenumber', 'Position']


def attach_kwargs(method):
    @wraps(method)
    def inner(view, req, resp, **kwargs):
        for k, v in kwargs.items():
            setattr(view, k, v)
        view.request = req
        return method(view, req, resp, **kwargs)
    return inner


class WithURL(type):

    urls = []

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs)
        if hasattr(cls, 'model'):
            for route in cls.routes():
                app.add_route(route, cls())
        return cls


class URLMixin(object, metaclass=WithURL):

    @classmethod
    def base_url(cls):
        return "/" + re.sub("([a-z])([A-Z])", "\g<1>/\g<2>", cls.__name__).lower()

    @classmethod
    def url_name(cls):
        return re.sub("([a-z])([A-Z])", "\g<1>-\g<2>", cls.__name__).lower()

    @classmethod
    def url_path(cls):
        return cls.base_url()


class BaseCRUD(URLMixin):
    identifiers = []
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

    def dispatch(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.key and self.key not in self.identifiers + ['id']:
            return self.error(400, 'Invalid identifier: {}'.format(self.ref))
        return super().dispatch(*args, **kwargs)

    def not_found(self, msg='Not found'):
        return self.error(404, msg)

    def error(self, status=400, msg='Invalid request'):
        return self.json(status, error=msg)

    @classmethod
    def routes(cls):
        return [
            cls.base_url(),
            # cls.base_url() + '/{id}',
            cls.base_url() + '/{identifier}:{id}',
            cls.base_url() + '/{identifier}:{id}/{route}',
            cls.base_url() + '/{identifier}:{id}/{route}/{route_id}',
        ]
        # return cls.base_url() + r'(?:(?P<key>[\w_]+)/(?P<ref>[\w_]+)/(?:(?P<route>[\w_]+)/(?:(?P<route_id>[\d]+)/)?)?)?$'  # noqa

    def get_object(self):
        try:
            return self.model.get(getattr(self.model, self.identifier) == self.id)
        except self.model.DoesNotExist:
            raise falcon.HTTPNotFound()

    @attach_kwargs
    def on_get(self, req, resp, **kwargs):
        identifier = kwargs.get('identifier')
        if identifier and identifier not in self.identifiers + ['id']:
            raise falcon.HTTPBadRequest('Invalid identifier: {}'.format(identifier), 'Invalid identifier: {}'.format(identifier))
        self.object = self.get_object()
        if getattr(self, 'route', None):
            name = 'on_get_{}'.format(self.route)
            view = getattr(self, name, None)
            if view and callable(view):
                return view(req, resp, **kwargs)
            else:
                raise falcon.HTTPBadRequest('Invalid route', 'Invalid route')
        resp.json(**self.object.as_resource)

    @attach_kwargs
    def on_post(self, req, resp, *args, **kwargs):
        if getattr(self, 'id', None):
            self.object = self.get_object()
            instance = self.object
        else:
            instance = None
        self.save_object(req.params, req, resp, instance)

    @attach_kwargs
    def on_put(self, req, resp, *args, **kwargs):
        self.object = self.get_object()
        data = req.json
        self.save_object(data, req, resp, self.object)

    def save_object(self, data, req, resp, instance=None):
        validator = self.model.validator(**data)
        if not validator.errors:
            try:
                self.object = validator.save(instance=instance)
            except self.object.ForcedVersionError:
                status = 409
                # Return original object.
                self.object = self.get_object()
            else:
                status = 200 if getattr(self, 'id', None) else 201
            resp.status = str(status)
            resp.json(**self.object.as_resource)
        else:
            resp.status = str(422)
            resp.json(errors=validator.errors)

    def get_limit(self):
        return min(int(self.request.params.get('limit', self.DEFAULT_LIMIT)),
                   self.MAX_LIMIT)

    def get_offset(self):
        try:
            return int(self.request.params.get('offset'))
        except (ValueError, TypeError):
            return 0

    def collection(self, req, resp, queryset):
        limit = self.get_limit()
        offset = self.get_offset()
        end = offset + limit
        count = queryset.count()
        kwargs = {
            'collection': list(queryset[offset:end]),
            'total': count,
        }
        url = '{}://{}{}'.format(self.request.protocol, self.request.host,
                                 self.request.path)
        if count > end:
            kwargs['next'] = '{}?{}'.format(url, urlencode({'offset': end}))
        if offset >= limit:
            kwargs['previous'] = '{}?{}'.format(url, urlencode({'offset': offset - limit}))  # noqa
        resp.json(**kwargs)

    def on_get_versions(self, req, resp, *args, **kwargs):
        self.object = self.get_object()
        if getattr(self, 'route_id', None):
            version = self.object.load_version(self.route_id)
            if not version:
                raise falcon.HTTPNotFound()
            resp.json(**version.as_resource)
        else:
            self.collection(req, resp, self.object.versions.as_resource())


class Position(BaseCRUD):
    model = models.Position


class Housenumber(BaseCRUD):
    identifiers = ['cia']
    model = models.HouseNumber

    def on_get_positions(self, *args, **kwargs):
        self.object = self.get_object()
        return self.collection(self.object.position_set.as_resource)


class Locality(BaseCRUD):
    model = models.Locality
    identifiers = ['fantoir']

    def on_get_housenumbers(self, *args, **kwargs):
        self.object = self.get_object()
        return self.collection(self.object.housenumber_set.as_resource)


class Street(Locality):
    model = models.Street
    identifiers = ['fantoir']


class Municipality(BaseCRUD):
    identifiers = ['siren', 'insee']
    model = models.Municipality

    def on_get_streets(self, req, resp, *args, **kwargs):
        self.object = self.get_object()
        self.collection(req, resp, self.object.street_set.as_resource())

    def on_get_localities(self, req, resp, *args, **kwargs):
        self.object = self.get_object()
        self.collection(req, resp, self.object.locality_set.as_resource())
