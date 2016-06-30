from urllib.parse import urlencode

import falcon
import peewee

from ban.core import models
from ban.auth import models as amodels

from .wsgi import app
from .auth import auth


__all__ = ['Municipality', 'Group', 'Postcode', 'Housenumber', 'Position']


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
        count = len(queryset)
        kwargs = {
            'collection': list(queryset[offset:end]),
            'total': count,
        }
        url = '{}://{}{}'.format(req.protocol, req.host, req.path)
        if count > end:
            query_string = req.params.copy()
            query_string.update({'offset': end})
            uri = '{}?{}'.format(url, urlencode(sorted(query_string.items())))
            kwargs['next'] = uri
            resp.add_link(uri, 'next')
        if offset >= limit:
            query_string = req.params.copy()
            query_string.update({'offset': offset - limit})
            uri = '{}?{}'.format(url, urlencode(sorted(query_string.items())))
            kwargs['previous'] = uri
            resp.add_link(uri, 'previous')
        resp.json(**kwargs)


class WithURL(type):

    urls = []

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs)
        if hasattr(cls, 'model'):
            app.register_resource(cls())
        return cls


class BaseCRUD(BaseCollection, metaclass=WithURL):

    order_by = None

    def get_object(self, identifier, **kwargs):
        try:
            return self.model.coerce(identifier)
        except self.model.DoesNotExist:
            raise falcon.HTTPNotFound()

    def get_collection(self, req, resp, **params):
        order_by = (self.order_by if self.order_by is not None
                    else [self.model.pk])
        return self.model.select().order_by(*order_by)

    @auth.protect
    @app.endpoint()
    def on_get(self, req, resp, **params):
        """Get {resource} collection."""
        qs = self.get_collection(req, resp, **params)
        self.collection(req, resp, qs.as_resource())

    @auth.protect
    @app.endpoint(path='/{identifier}')
    def on_get_resource(self, req, resp, **params):
        """Get {resource} with 'identifier'."""
        instance = self.get_object(**params)
        resp.json(**instance.as_resource)

    @auth.protect
    @app.endpoint(path='/{identifier}')
    def on_post_resource(self, req, resp, *args, **params):
        """Patch {resource} with 'identifier'."""
        instance = self.get_object(**params)
        self.save_object(req.params, req, resp, instance, **params)

    @auth.protect
    @app.endpoint()
    def on_post(self, req, resp, *args, **params):
        """Create {resource}"""
        self.save_object(req.params, req, resp, **params)

    @auth.protect
    @app.endpoint(path='/{identifier}')
    def on_put_resource(self, req, resp, *args, **params):
        """Update {resource}"""
        instance = self.get_object(**params)
        data = req.json
        self.save_object(data, req, resp, instance, **params)

    @auth.protect
    @app.endpoint(path='/{identifier}')
    def on_patch_resource(self, req, resp, *args, **params):
        """Patch {resource}"""
        instance = self.get_object(**params)
        data = req.json
        self.save_object(data, req, resp, instance, **params)

    def save_object(self, data, req, resp, instance=None, **kwargs):
        update = instance and req.method != 'PUT'
        validator = self.model.validator(update=update, instance=instance,
                                         **data)
        if not validator.errors:
            try:
                instance = validator.save()
            except models.Model.ForcedVersionError:
                status = falcon.HTTP_CONFLICT
                # Return original object.
                instance = self.get_object(**kwargs)
            else:
                if 'identifier' in kwargs:
                    status = falcon.HTTP_OK
                else:
                    status = falcon.HTTP_CREATED
                    resp.set_header('Location',
                                    self.resource_uri(req, instance))
            resp.status = status
            resp.json(**instance.as_resource)
        else:
            resp.status = falcon.HTTP_UNPROCESSABLE_ENTITY
            resp.json(errors=validator.errors)

    @auth.protect
    @app.endpoint(path='/{identifier}')
    def on_delete_resource(self, req, resp, *args, **params):
        """Delete {resource}."""
        instance = self.get_object(**params)
        try:
            instance.delete_instance()
        except:
            resp.status = falcon.HTTP_CONFLICT
        else:
            resp.status = falcon.HTTP_NO_CONTENT


class VersionnedResource(BaseCRUD):

    @auth.protect
    @app.endpoint('/{identifier}/versions')
    def on_get_versions(self, req, resp, *args, **kwargs):
        """Get resource versions."""
        instance = self.get_object(**kwargs)
        self.collection(req, resp, instance.versions.as_resource())

    @auth.protect
    @app.endpoint('/{identifier}/versions/{version}')
    def on_get_version(self, req, resp, version, **kwargs):
        """Get {resource} version corresponding to 'version' number."""
        instance = self.get_object(**kwargs)
        version = instance.load_version(version)
        if not version:
            raise falcon.HTTPNotFound()
        resp.json(**version.as_resource)


class BboxResource:

    def get_bbox(self, req):
        bbox = {}
        req.get_param_as_float('north', store=bbox)
        req.get_param_as_float('south', store=bbox)
        req.get_param_as_float('east', store=bbox)
        req.get_param_as_float('west', store=bbox)
        if not len(bbox) == 4:
            return None
        return bbox


class Position(VersionnedResource, BboxResource):
    """Manipulate position resources."""
    model = models.Position

    def get_collection(self, req, resp, **kwargs):
        qs = super().get_collection(req, resp, **kwargs)
        bbox = self.get_bbox(req)
        if bbox:
            qs = (qs.where(models.Position.center.in_bbox(**bbox)))
        return qs

    @auth.protect
    @app.endpoint('/{identifier}/positions')
    def on_get_positions(self, req, resp, *args, **kwargs):
        """Retrieve {resource} positions."""
        instance = self.get_object(**kwargs)
        qs = instance.position_set.as_resource_list()
        self.collection(req, resp, qs)


class Housenumber(VersionnedResource, BboxResource):
    model = models.HouseNumber
    order_by = [peewee.SQL('number ASC NULLS FIRST'),
                peewee.SQL('ordinal ASC NULLS FIRST')]

    def get_collection(self, req, resp, **kwargs):
        qs = super().get_collection(req, resp, **kwargs)
        bbox = self.get_bbox(req)
        if bbox:
            qs = (qs.join(models.Position)
                    .where(models.Position.center.in_bbox(**bbox))
                    .group_by(models.HouseNumber.pk)
                    .order_by(models.HouseNumber.pk))
        return qs

    @auth.protect
    @app.endpoint('/{identifier}/positions')
    def on_get_positions(self, req, resp, *args, **kwargs):
        """Retrieve {resource} positions."""
        instance = self.get_object(**kwargs)
        qs = instance.position_set.as_resource_list()
        self.collection(req, resp, qs)


class WithHousenumbers(VersionnedResource):

    @auth.protect
    @app.endpoint('/{identifier}/housenumbers')
    def on_get_housenumbers(self, req, resp, *args, **kwargs):
        """Retrieve {resource} housenumbers."""
        instance = self.get_object(**kwargs)
        # We evaluate the qs ourselves here, because it's a CompoundSelect
        # that does not know about our SelectQuery custom methods (like
        # `as_resource_list`), and CompoundSelect is hardcoded in peewee
        # SelectQuery, and we'd need to copy-paste code to be able to use
        # a custom CompoundQuery class instead.
        self.collection(req, resp, [h.as_relation
                                    for h in instance.housenumbers])


class Group(WithHousenumbers):
    model = models.Group


class Postcode(WithHousenumbers):
    model = models.PostCode
    order_by = [model.code, model.municipality]


class Municipality(VersionnedResource):
    model = models.Municipality
    order_by = [model.insee]

    @auth.protect
    @app.endpoint('/{identifier}/groups')
    def on_get_groups(self, req, resp, *args, **kwargs):
        """Retrieve {resource} groups."""
        instance = self.get_object(**kwargs)
        self.collection(req, resp, instance.groups.as_resource_list())


class User(BaseCRUD):
    model = amodels.User
