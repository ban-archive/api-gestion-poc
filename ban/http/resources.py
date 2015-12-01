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


class BaseCollection:
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

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
            query_string = req.params.copy()
            query_string.update({'offset': end})
            kwargs['next'] = '{}?{}'.format(url, urlencode(query_string))
        if offset >= limit:
            query_string = req.params.copy()
            query_string.update({'offset': offset - limit})
            kwargs['previous'] = '{}?{}'.format(url, urlencode(query_string))
        resp.json(**kwargs)


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
    def url_path(cls):
        return cls.base_url()


class BaseCRUD(URLMixin, BaseCollection):

    @classmethod
    def routes(cls):
        return [
            cls.base_url(),
            cls.base_url() + '/{id}',
            cls.base_url() + '/{id}/{route}',
            cls.base_url() + '/{id}/{route}/{route_id}',
        ]

    def get_object(self, id, **kwargs):
        try:
            return self.model.coerce(id)
        except self.model.DoesNotExist:
            raise falcon.HTTPNotFound()

    def get_collection(self, req, resp, **params):
        return self.model.select()

    @dispatch_route
    def on_get(self, req, resp, **params):
        if 'id' in params:
            instance = self.get_object(**params)
            resp.json(**instance.as_resource)
        else:
            qs = self.get_collection(req, resp, **params)
            self.collection(req, resp, qs.as_resource())

    @auth.protect
    def on_post(self, req, resp, *args, **params):
        if 'id' in params:
            instance = self.get_object(**params)
        else:
            instance = None
        self.save_object(req.params, req, resp, instance, **params)

    @auth.protect
    def on_put(self, req, resp, *args, **params):
        instance = self.get_object(**params)
        data = req.json
        self.save_object(data, req, resp, instance, **params)

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

    def get_bbox(self, req):
        bbox = {}
        req.get_param_as_int('north', store=bbox)
        req.get_param_as_int('south', store=bbox)
        req.get_param_as_int('east', store=bbox)
        req.get_param_as_int('west', store=bbox)
        if any(v is None for v in bbox.values()):
            return None
        return bbox

    def get_collection(self, req, resp, **kwargs):
        qs = super().get_collection(req, resp, **kwargs)
        bbox = self.get_bbox(req)
        if bbox:
            qs = (qs.join(models.Position)
                    .where(models.Position.center.in_bbox(**bbox))
                    .group_by(models.HouseNumber.id)
                    .order_by(models.HouseNumber.id))
        return qs

    def on_get_positions(self, req, resp, *args, **kwargs):
        instance = self.get_object(**kwargs)
        qs = instance.position_set.as_resource_list()
        self.collection(req, resp, qs)


class Locality(VersionnedResource):
    model = models.Locality

    def on_get_housenumbers(self, req, resp, *args, **kwargs):
        instance = self.get_object(**kwargs)
        self.collection(req, resp, instance.housenumber_set.as_resource_list())


class Street(Locality):
    model = models.Street


class Municipality(VersionnedResource):
    model = models.Municipality

    def on_get_streets(self, req, resp, *args, **kwargs):
        instance = self.get_object(**kwargs)
        self.collection(req, resp, instance.street_set.as_resource_list())

    def on_get_localities(self, req, resp, *args, **kwargs):
        instance = self.get_object(**kwargs)
        self.collection(req, resp, instance.locality_set.as_resource_list())


class User(BaseCRUD):
    model = amodels.User
