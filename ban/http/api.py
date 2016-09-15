from datetime import timezone
from urllib.parse import urlencode

from flask import request, make_response
from flask_restplus import Api, Resource, abort
from werkzeug.routing import BaseConverter, ValidationError
from dateutil.parser import parse as parse_date
import peewee

from ban.core import models
from ban.core.encoder import dumps

from ban.http.wsgi import app
from ban.http.auth import auth

api = Api(app)


def instance_or_404(func):
    def wrapper(self, **kwargs):
        if kwargs.get('identifier'):
            try:
                instance = self.model.coerce(kwargs['identifier'])
            except self.model.DoesNotExist:
                # TODO Flask changes the 404 message, which we don't want.
                abort(404, message='Resource not found')
            kwargs['instance'] = instance
        return func(self, **kwargs)
    return wrapper


def get_bbox(args):
    bbox = {}
    params = ['north', 'south', 'east', 'west']
    for param in params:
        try:
            bbox[param] = float(args.get(param))
        except ValueError:
            abort(400, 'Invalid value for {}: {}'.format(param,
                                                         args.get(param)))
        except TypeError:
            # None (param not set).
            continue
    if not len(bbox) == 4:
        return None
    return bbox


class DateTimeConverter(BaseConverter):

    def to_python(self, value):
        try:
            value = parse_date(value)
        except ValueError:
            raise ValidationError
        # Be smart, imply that naive dt are in the same tz the API
        # exposes, which is UTC.
        if not value.tzinfo:
            value = value.replace(tzinfo=timezone.utc)
        return value


app.url_map.converters['datetime'] = DateTimeConverter


@api.representation('application/json')
def json(data, code, headers):
    resp = make_response(dumps(data), code)
    resp.headers.extend(headers)
    return resp


class BaseCollection(Resource):

    filters = []
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

    def get_limit(self):
        return min(int(request.args.get('limit', self.DEFAULT_LIMIT)),
                   self.MAX_LIMIT)

    def get_offset(self):
        try:
            return int(request.args.get('offset'))
        except (ValueError, TypeError):
            return 0

    def collection(self, queryset):
        limit = self.get_limit()
        offset = self.get_offset()
        end = offset + limit
        count = len(queryset)
        data = {
            'collection': list(queryset[offset:end]),
            'total': count,
        }
        headers = {}
        url = request.base_url
        if count > end:
            query_string = request.args.copy()
            query_string['offset'] = end
            uri = '{}?{}'.format(url, urlencode(sorted(query_string.items())))
            data['next'] = uri
            # resp.add_link(uri, 'next')
        if offset >= limit:
            query_string = request.args.copy()
            query_string['offset'] = offset - limit
            uri = '{}?{}'.format(url, urlencode(sorted(query_string.items())))
            data['previous'] = uri
            # resp.add_link(uri, 'previous')
        return data, 200, headers


class BaseResourceCollection(BaseCollection):
    order_by = None

    def get(self):
        qs = self.get_queryset()
        if qs is None:
            return self.collection([])
        if not isinstance(qs, list):
            order_by = (self.order_by if self.order_by is not None
                        else [self.model.pk])
            qs = qs.order_by(*order_by).as_resource_list()
        return self.collection(qs)

    def get_queryset(self):
        qs = self.model.select()
        for key in self.filters:
            values = request.args.getlist(key)
            if values:
                func = 'filter_{}'.format(key)
                if hasattr(self, func):
                    qs = getattr(self, func)(qs)
                    continue
                field = getattr(self.model, key)
                try:
                    values = list(map(field.coerce, values))
                except ValueError:
                    abort('400', 'Invalid value for filter {}'.format(key))
                except peewee.DoesNotExist:
                    # Return an empty collection as the fk is not found.
                    return None
                qs = qs.where(field << values)
        return qs


@api.route('/municipality/', endpoint='municipality-collection')
class MunicipalityCollection(BaseResourceCollection):
    model = models.Municipality
    order_by = [model.insee]


@api.route('/postcode/')
class PostCodeCollection(BaseResourceCollection):
    model = models.PostCode
    order_by = [model.code, model.municipality]
    filters = ['code', 'municipality']


@api.route('/group/')
class GroupCollection(BaseResourceCollection):
    filters = ['municipality']
    model = models.Group


@api.route('/housenumber/', endpoint='housenumber-collection')
class HouseNumberCollection(BaseResourceCollection):
    filters = ['parent', 'postcode', 'ancestors', 'group']
    model = models.HouseNumber
    order_by = [peewee.SQL('number ASC NULLS FIRST'),
                peewee.SQL('ordinal ASC NULLS FIRST')]

    def filter_ancestors_and_group(self, qs):
        # ancestors is a m2m so we cannot use the basic filtering
        # from self.filters.
        ancestors = request.args.getlist('ancestors')
        group = request.args.getlist('group')  # Means parent + ancestors.
        values = group or ancestors
        values = list(map(self.model.ancestors.coerce, values))
        parent_qs = qs.where(self.model.parent << values) if group else None
        if values:
            m2m = self.model.ancestors.get_through_model()
            qs = (qs.join(m2m, on=(m2m.housenumber == self.model.pk))
                    .where(m2m.group << values))
            if parent_qs:
                qs = (parent_qs | qs)
            # We evaluate the qs ourselves here, because it's a CompoundSelect
            # that does not know about our SelectQuery custom methods (like
            # `as_resource_list`), and CompoundSelect is hardcoded in peewee
            # SelectQuery, and we'd need to copy-paste code to be able to use
            # a custom CompoundQuery class instead.
            qs = [h.as_relation for h in qs]
        return qs

    def filter_ancestors(self, qs):
        return self.filter_ancestors_and_group(qs)

    def filter_group(self, qs):
        return self.filter_ancestors_and_group(qs)

    def get_queryset(self):
        qs = super().get_queryset()
        bbox = get_bbox(request.args)
        if bbox:
            qs = (qs.join(models.Position)
                    .where(models.Position.center.in_bbox(**bbox))
                    .group_by(models.HouseNumber.pk)
                    .order_by(models.HouseNumber.pk))
        return qs


@api.route('/position/')
class PositionCollection(BaseResourceCollection):
    model = models.Position
    filters = ['kind', 'housenumber']

    def get_queryset(self):
        qs = super().get_queryset()
        bbox = get_bbox(request.args)
        if bbox:
            qs = qs.where(models.Position.center.in_bbox(**bbox))
        return qs


class BaseVersionCollection(BaseCollection):
    def get(self, identifier):
        instance = self.model.coerce(identifier)
        return self.collection(instance.versions.as_resource())


@api.route('/municipality/<identifier>/versions/')
class MunicipalityVersionCollection(BaseVersionCollection):
    model = models.Municipality


@api.route('/group/<identifier>/versions/')
class GroupVersionCollection(BaseVersionCollection):
    model = models.Group


class BaseVersion(Resource):
    @instance_or_404
    def get(self, identifier, ref, instance):
        instance = self.model.coerce(identifier)
        version = instance.load_version(ref)
        if not version:
            abort(404)
        return version.as_resource

    @instance_or_404
    def post(self, identifier, ref, instance):
        instance = self.model.coerce(identifier)
        version = instance.load_version(ref)
        if not version:
            abort(404)
        flag = request.json.get('flag')
        if flag is True:
            version.flag()
        elif flag is False:
            version.unflag()
        else:
            abort(400, message='Body should contain a "flag" boolean key')


@api.route('/municipality/<identifier>/versions/<int:ref>/',
           endpoint='municipality-version-by-sequential')
@api.route('/municipality/<identifier>/versions/<datetime:ref>/',
           endpoint='municipality-version-by-date')
class MunicipalityVersion(BaseVersion):
    model = models.Municipality


@api.route('/group/<identifier>/versions/<int:ref>/')
@api.route('/group/<identifier>/versions/<datetime:ref>/')
class GroupVersion(BaseVersion):
    model = models.Group


@api.route('/postcode/<identifier>/versions/<int:ref>/')
@api.route('/postcode/<identifier>/versions/<datetime:ref>/')
class PostCodeVersion(BaseVersion):
    model = models.PostCode


@api.route('/housenumber/<identifier>/versions/<int:ref>/')
@api.route('/housenumber/<identifier>/versions/<datetime:ref>/')
class HouseNumberVersion(BaseVersion):
    model = models.HouseNumber


@api.route('/position/<identifier>/versions/<int:ref>/')
@api.route('/position/<identifier>/versions/<datetime:ref>/')
class PositionVersion(BaseVersion):
    model = models.Position


class BaseResource(Resource):

    def save_object(self, instance=None, update=True):
        validator = self.model.validator(update=update, instance=instance,
                                         **request.json)
        if validator.errors:
            abort(422, errors=validator.errors)
        try:
            instance = validator.save()
        except models.Model.ForcedVersionError as e:
            abort(409, str(e))
        return instance

    @auth.require_oauth()
    @instance_or_404
    def get(self, identifier, instance):
        return instance.as_resource

    @auth.require_oauth()
    @instance_or_404
    def post(self, identifier=None, instance=None):
        if instance:
            return self.patch(instance)
        instance = self.save_object()
        headers = {'Location': api.url_for(self, identifier=instance.id)}
        return instance.as_resource, 201, headers

    @auth.require_oauth()
    @instance_or_404
    def patch(self, identifier, instance):
        instance = self.save_object(instance)
        return instance.as_resource

    @auth.require_oauth()
    @instance_or_404
    def put(self, identifier, instance):
        instance = self.save_object(instance, update=False)
        return instance.as_resource

    @auth.require_oauth()
    @instance_or_404
    def delete(self, identifier, instance):
        try:
            instance.delete_instance()
        except peewee.IntegrityError:
            # This model was still pointed by a FK.
            abort(409)
        return {'resource_id': identifier}


# Keep the path with identifier first to make it the URL for reverse.
@api.route('/municipality/<string:identifier>/',
           endpoint='municipality-resource')
@api.route('/municipality/', endpoint='municipality-post')
class Municipality(BaseResource):
    model = models.Municipality


# Keep the path with identifier first to make it the URL for reverse.
@api.route('/postcode/<string:identifier>/', endpoint='postcode-resource')
@api.route('/postcode/', endpoint='postcode-post')
class PostCode(BaseResource):
    model = models.PostCode


# Keep the path with identifier first to make it the URL for reverse.
@api.route('/group/<string:identifier>/')
@api.route('/group/')
class Group(BaseResource):
    model = models.Group


# Keep the path with identifier first to make it the URL for reverse.
@api.route('/housenumber/<string:identifier>/',
           endpoint='housenumber-resource')
@api.route('/housenumber/', endpoint='housenumber-post')
class HouseNumber(BaseResource):
    model = models.HouseNumber


# Keep the path with identifier first to make it the URL for reverse.
@api.route('/position/<string:identifier>/')
@api.route('/position/')
class Position(BaseResource):
    model = models.Position


if __name__ == '__main__':
    app.run(debug=True)
