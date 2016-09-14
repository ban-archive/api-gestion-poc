from datetime import timezone
from urllib.parse import urlencode

from flask import Flask, request, make_response
from flask_restplus import Api, Resource, abort
from werkzeug.routing import BaseConverter, ValidationError
from dateutil.parser import parse as parse_date
import peewee


from ban.core import models
from ban.core.encoder import dumps

app = Flask(__name__)
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
    def get(self):
        qs = self.model.select()
        for key in self.filters:
            values = request.args.getlist(key)
            if values:
                field = getattr(self.model, key)
                try:
                    values = list(map(field.coerce, values))
                except ValueError:
                    abort('400', 'Invalid value for filter {}'.format(key))
                except peewee.DoesNotExist:
                    # Return an empty collection as the fk is not found.
                    return self.collection([])
                qs = qs.where(field << values)
        return self.collection(qs.as_resource_list())


@api.route('/municipality/')
class MunicipalityCollection(BaseResourceCollection):
    model = models.Municipality


@api.route('/group/')
class GroupCollection(BaseResourceCollection):
    filters = ['municipality']
    model = models.Group


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


@api.route('/municipality/<identifier>/versions/<int:ref>/')
@api.route('/municipality/<identifier>/versions/<datetime:ref>/')
class MunicipalityVersion(BaseVersion):
    model = models.Municipality


@api.route('/group/<identifier>/versions/<int:ref>/')
@api.route('/group/<identifier>/versions/<datetime:ref>/')
class GroupVersion(BaseVersion):
    model = models.Group


class BaseResource(Resource):

    def save_object(self, instance=None, update=True):
        validator = self.model.validator(update=update, instance=instance,
                                         **request.json)
        if validator.errors:
            abort(422, **validator.errors)
        try:
            instance = validator.save()
        except models.Model.ForcedVersionError as e:
            abort(409, str(e))
        return instance

    @instance_or_404
    def get(self, identifier, instance):
        return instance.as_resource

    @instance_or_404
    def post(self, identifier=None, instance=None):
        if instance:
            return self.patch(instance)
        instance = self.save_object()
        headers = {'Location': api.url_for(self, identifier=instance.id)}
        return instance.as_resource, 201, headers

    @instance_or_404
    def patch(self, identifier, instance):
        instance = self.save_object(instance)
        return instance.as_resource

    @instance_or_404
    def put(self, identifier, instance):
        instance = self.save_object(instance, update=False)
        return instance.as_resource

    @instance_or_404
    def delete(self, identifier, instance):
        try:
            instance.delete_instance()
        except peewee.IntegrityError:
            # This model was still pointed by a FK.
            abort(409)
        return {'resource_id': identifier}


# Keep the path with identifier first to make it the URL for reverse.
@api.route('/municipality/<string:identifier>/')
@api.route('/municipality/')
class Municipality(BaseResource):
    model = models.Municipality


# Keep the path with identifier first to make it the URL for reverse.
@api.route('/group/<string:identifier>/')
@api.route('/group/')
class Group(BaseResource):
    model = models.Group


if __name__ == '__main__':
    app.run(debug=True)
