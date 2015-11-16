import re
from urllib.parse import urlencode

import falcon

# from ban.auth.decorators import protected
from ban.core import models
from ban.auth import models as amodels

from .wsgi import app
from .auth import auth


__all__ = ['Municipality', 'Street', 'Locality', 'Housenumber', 'Position']


def dispatch_route(method):
    def wrapper(resource, req, resp, **params):
        # TODO: custom router instead, so routes are compiled on load.
        if 'route' in params:
            name = 'on_{}_{}'.format(req.method.lower(), params['route'])
            view = getattr(resource, name, None)
            if view and callable(view):
                return view(req, resp, **params)
            else:
                raise falcon.HTTPNotFound()
        method(resource, req, resp, **params)
    return wrapper


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
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

    def not_found(self, msg='Not found'):
        return self.error(404, msg)

    def error(self, status=400, msg='Invalid request'):
        return self.json(status, error=msg)

    @classmethod
    def routes(cls):
        # Falcon does not allow to have those two routes in the same time:
        # '/path/{id}'
        # '/path/{identifier}:{id}'
        return [
            cls.base_url(),
            # cls.base_url() + '/{id}',
            cls.base_url() + '/{id}',
            cls.base_url() + '/{id}/{route}',
            cls.base_url() + '/{id}/{route}/{route_id}',
        ]
        # return cls.base_url() + r'(?:(?P<key>[\w_]+)/(?P<ref>[\w_]+)/(?:(?P<route>[\w_]+)/(?:(?P<route_id>[\d]+)/)?)?)?$'  # noqa

    def get_object(self, id, **kwargs):
        try:
            return self.model.coerce(id)
        except self.model.DoesNotExist:
            raise falcon.HTTPNotFound()

    @dispatch_route
    def on_get(self, req, resp, **params):
        instance = self.get_object(**params)
        resp.json(**instance.as_resource)

    @auth.protect
    def on_post(self, req, resp, *args, **kwargs):
        if 'id' in kwargs:
            instance = self.get_object(**kwargs)
        else:
            instance = None
        self.save_object(req.params, req, resp, instance, **kwargs)

    @auth.protect
    def on_put(self, req, resp, *args, **kwargs):
        instance = self.get_object(**kwargs)
        data = req.json
        self.save_object(data, req, resp, instance, **kwargs)

    def save_object(self, data, req, resp, instance=None, **kwargs):
        validator = self.model.validator(**data)
        if not validator.errors:
            try:
                instance = validator.save(instance=instance)
            except instance.ForcedVersionError:
                status = falcon.HTTP_CONFLICT
                # Return original object.
                instance = self.get_object(**kwargs)
            else:
                status = falcon.HTTP_OK if 'id' in kwargs \
                                                       else falcon.HTTP_CREATED
            resp.status = str(status)
            resp.json(**instance.as_resource)
        else:
            # See https://github.com/falconry/falcon/issues/627.
            resp.status = str(422)
            resp.json(errors=validator.errors)

    def get_limit(self, req):
        return min(int(req.params.get('limit', self.DEFAULT_LIMIT)),
                   self.MAX_LIMIT)

    def get_offset(self, req):
        try:
            return int(req.params.get('offset'))
        except (ValueError, TypeError):
            return 0

    def collection(self, req, resp, queryset):
        limit = self.get_limit(req)
        offset = self.get_offset(req)
        end = offset + limit
        count = queryset.count()
        kwargs = {
            'collection': list(queryset[offset:end]),
            'total': count,
        }
        url = '{}://{}{}'.format(req.protocol, req.host, req.path)
        if count > end:
            kwargs['next'] = '{}?{}'.format(url, urlencode({'offset': end}))
        if offset >= limit:
            kwargs['previous'] = '{}?{}'.format(url, urlencode({'offset': offset - limit}))  # noqa
        resp.json(**kwargs)


class VersionnedResource(BaseCRUD):

    def on_get_versions(self, req, resp, *args, **kwargs):
        instance = self.get_object(**kwargs)
        route_id = kwargs.get('route_id')
        if route_id:
            version = instance.load_version(route_id)
            if not version:
                raise falcon.HTTPNotFound()
            resp.json(**version.as_resource)
        else:
            self.collection(req, resp, instance.versions.as_resource())


class Position(VersionnedResource):
    model = models.Position


class Housenumber(VersionnedResource):
    model = models.HouseNumber

    def on_get_positions(self, *args, **kwargs):
        instance = self.get_object(**kwargs)
        return self.collection(instance.position_set.as_resource)


class Locality(VersionnedResource):
    model = models.Locality

    def on_get_housenumbers(self, *args, **kwargs):
        instance = self.get_object(**kwargs)
        return self.collection(instance.housenumber_set.as_resource)


class Street(Locality):
    model = models.Street


class Municipality(VersionnedResource):
    model = models.Municipality

    def on_get_streets(self, req, resp, *args, **kwargs):
        instance = self.get_object(**kwargs)
        self.collection(req, resp, instance.street_set.as_resource())

    def on_get_localities(self, req, resp, *args, **kwargs):
        instance = self.get_object(**kwargs)
        self.collection(req, resp, instance.locality_set.as_resource())


class User(BaseCRUD):
    model = amodels.User
