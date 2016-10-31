from io import StringIO
from urllib.parse import urlencode

import peewee
from flask import request, url_for

from ban.auth import models as amodels
from ban.commands.bal import bal
from ban.core import context, models, versioning
from ban.core.encoder import dumps
from ban.core.exceptions import (IsDeletedError, MultipleRedirectsError,
                                 RedirectError, ResourceLinkedError)
from ban.http.auth import auth
from ban.http.wsgi import app
from ban.utils import parse_mask

from .utils import abort, get_bbox, link


class CollectionEndpoint:

    filters = []
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 1000

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
            link(headers, uri, 'next')
        if offset >= limit:
            query_string = request.args.copy()
            query_string['offset'] = offset - limit
            uri = '{}?{}'.format(url, urlencode(sorted(query_string.items())))
            data['previous'] = uri
            link(headers, uri, 'previous')
        return data, 200, headers


class ModelEndpoint(CollectionEndpoint):
    endpoints = {}
    order_by = None

    def get_object(self, identifier):
        endpoint = '{}-get-resource'.format(self.__class__.__name__.lower())
        try:
            instance = self.model.coerce(identifier)
        except self.model.DoesNotExist:
            abort(404, error='Resource with identifier `{}` does not exist.'
                  .format(identifier))
        except RedirectError as e:
            headers = {'Location': url_for(endpoint, identifier=e.redirect)}
            abort(302, headers=headers)
        except MultipleRedirectsError as e:
            headers = {}
            choices = []
            for redirect in e.redirects:
                uri = url_for(endpoint, identifier=redirect)
                link(headers, uri, 'alternate')
                choices.append(uri)
            abort(300, headers=headers, choices=choices)
        except IsDeletedError as err:
            if request.method not in ['GET', 'PUT']:
                abort(410, error='Resource `{}` is deleted'.format(identifier))
            instance = err.instance
        return instance

    def save_object(self, instance=None, update=False):
        validator = self.model.validator(update=update, instance=instance,
                                         **request.json or {})
        if validator.errors:
            abort(422, error='Invalid data', errors=validator.errors)
        try:
            instance = validator.save()
        except models.Model.ForcedVersionError as e:
            abort(409, error=str(e))
        return instance

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
                    abort(400, error='Invalid value for filter {}'.format(key))
                except peewee.DoesNotExist:
                    # Return an empty collection as the fk is not found.
                    return None
                qs = qs.where(field << values)
        return qs

    def get_mask(self):
        fields = request.args.get('fields', '*')
        return parse_mask(fields)

    def get_collection_mask(self):
        fields = request.args.get('fields')
        if not fields:
            fields = ','.join(self.model.collection_fields)
        return parse_mask(fields)

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('', methods=['GET'])
    def get_collection(self):
        """Get {resource} collection.

        responses:
            200:
                description: Get {resource} collection.
                schema:
                    type: object
                    properties:
                      collection:
                        name: collection
                        type: array
                        items:
                          $ref: '#/definitions/{resource}'
                      total:
                        name: total
                        type: integer
                        description: total resources available
        """
        qs = self.get_queryset()
        if qs is None:
            return self.collection([])
        if not isinstance(qs, list):
            order_by = (self.order_by if self.order_by is not None
                        else [self.model.pk])
            qs = qs.order_by(*order_by).serialize(self.get_collection_mask())
        try:
            return self.collection(qs)
        except ValueError as e:
            abort(400, error=str(e))

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>', methods=['GET'])
    def get_resource(self, identifier):
        """Get {resource} with 'identifier'.

        parameters:
            - $ref: '#/parameters/identifier'
        responses:
            200:
                description: Get {resource} instance.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                description: Resource is deleted.
                schema:
                    $ref: '#/definitions/{resource}'
        """
        instance = self.get_object(identifier)
        status = 410 if instance.deleted_at else 200
        try:
            return instance.serialize(self.get_mask()), status
        except ValueError as e:
            abort(400, error=str(e))

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>', methods=['POST'])
    def post_resource(self, identifier):
        """Patch {resource} with 'identifier'.

        parameters:
            - $ref: '#/parameters/identifier'
        responses:
            200:
                description: Instance has been updated successfully.
                schema:
                    $ref: '#/definitions/{resource}'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                description: Resource is deleted.
                schema:
                    $ref: '#/definitions/Error'
            422:
                description: Invalid data.
                schema:
                    $ref: '#/definitions/Error'
        """
        instance = self.get_object(identifier)
        instance = self.save_object(instance, update=True)
        return instance.as_resource

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('', methods=['POST'])
    def post(self):
        """Create {resource}

        responses:
            201:
                description: Instance has been created successfully.
                schema:
                    $ref: '#/definitions/{resource}'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                description: Resource is deleted.
                schema:
                    $ref: '#/definitions/Error'
            422:
                description: Invalid data.
                schema:
                    $ref: '#/definitions/Error'
        """
        instance = self.save_object()
        endpoint = '{}-get-resource'.format(self.__class__.__name__.lower())
        headers = {'Location': url_for(endpoint, identifier=instance.id)}
        return instance.as_resource, 201, headers

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>', methods=['PATCH'])
    def patch(self, identifier):
        """Patch {resource}

        parameters:
            - $ref: '#/parameters/identifier'
        responses:
            200:
                description: Instance has been updated successfully.
                schema:
                    $ref: '#/definitions/{resource}'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                description: Resource is deleted.
                schema:
                    $ref: '#/definitions/Error'
            422:
                description: Invalid data.
                schema:
                    $ref: '#/definitions/Error'
        """
        instance = self.get_object(identifier)
        instance = self.save_object(instance, update=True)
        return instance.as_resource

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>', methods=['PUT'])
    def put(self, identifier):
        """Replace or restore {resource}.

        parameters:
            - $ref: '#/parameters/identifier'
        responses:
            200:
                description: Instance has been replaced successfully.
                schema:
                    $ref: '#/definitions/{resource}'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                description: Resource is deleted.
                schema:
                    $ref: '#/definitions/Error'
            422:
                description: Invalid data.
                schema:
                    $ref: '#/definitions/Error'
        """
        instance = self.get_object(identifier)
        if instance.deleted_at:
            # We want to create only one new version for a restore. Change the
            # property here, but let the save_object do the actual save
            # if the data is valid.
            instance.deleted_at = None
        instance = self.save_object(instance)
        return instance.as_resource

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>', methods=['DELETE'])
    def delete(self, identifier):
        """Delete {resource}.

        parameters:
            - $ref: '#/parameters/identifier'
        responses:
            204:
                description: Instance has been deleted successfully.
                schema:
                    $ref: '#/definitions/{resource}'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                description: Resource is already deleted.
                schema:
                    $ref: '#/definitions/Error'
        """
        instance = self.get_object(identifier)
        try:
            instance.mark_deleted()
        except ResourceLinkedError as e:
            abort(409, error=str(e))
        return {'resource_id': identifier}


class VersionedModelEnpoint(ModelEndpoint):
    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>/versions', methods=['GET'])
    def get_versions(self, identifier):
        """Get resource versions.

        parameters:
            - $ref: '#/parameters/identifier'
        responses:
            200:
                description: Version collection for resource {resource}.
                schema:
                    type: array
                    items:
                        $ref: '#/definitions/Version'
        """
        instance = self.get_object(identifier)
        return self.collection(instance.versions.serialize())

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>/versions/<datetime:ref>', methods=['GET'])
    @app.endpoint('/<identifier>/versions/<int:ref>', methods=['GET'])
    def get_version(self, identifier, ref):
        """Get {resource} version corresponding to 'ref' number or datetime.

        parameters:
            - $ref: '#/parameters/identifier'
            - name: ref
              in: path
              type: string
              required: true
              description: version reference, either a date or an increment.
        responses:
            200:
                description: get specific Version for resource {resource}.
                schema:
                    $ref: '#/definitions/Version'
        """
        instance = self.get_object(identifier)
        version = instance.load_version(ref)
        if not version:
            abort(404, error='Version reference `{}` not found'.format(ref))
        return version.serialize()

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>/versions/<int:ref>/flag', methods=['POST'])
    def post_version(self, identifier, ref):
        """Flag a version.

        parameters:
            - $ref: '#/parameters/identifier'
            - name: ref
              in: path
              type: string
              required: true
              description: version reference, either a date or an increment.
        responses:
            204:
                description: version flag was updated.
        """
        instance = self.get_object(identifier)
        version = instance.load_version(ref)
        if not version:
            abort(404, error='Version reference `{}` not found'.format(ref))
        status = request.json.get('status')
        if status is True:
            version.flag()
        elif status is False:
            version.unflag()
        else:
            abort(400, error='Body should contain a `status` boolean key')

    @auth.require_oauth()
    @app.endpoint('/<identifier>/redirects/<old>', methods=['PUT', 'DELETE'])
    def put_delete_redirects(self, identifier, old):
        """Create a new redirect to this resource.

        parameters:
            - $ref: '#/parameters/identifier'
            - name: old
              in: path
              type: string
              required: true
              description: old identifier.
        responses:
            204:
                description: redirect was successful.
            201:
                description: redirect was created.
            422:
                description: error while creating the redirect.
        """
        instance = self.get_object(identifier)
        old_identifier, old_value = old.split(':')
        if request.method == 'PUT':
            try:
                versioning.Redirect.add(instance, old_identifier, old_value)
            except ValueError as e:
                abort(422, error=str(e))
            return '', 201
        elif request.method == 'DELETE':
            versioning.Redirect.remove(instance, old_identifier, old_value)
            return '', 204

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>/redirects', methods=['GET'])
    def get_redirects(self, identifier):
        """Get a collection of Redirect pointing to this resource.

        parameters:
            - $ref: '#/parameters/identifier'
        responses:
            200:
                description: A list of redirects.
        """
        instance = self.get_object(identifier)
        cls = versioning.Redirect
        qs = cls.select().where(cls.model_id == instance.id)
        return self.collection(qs.serialize())


@app.resource
class Municipality(VersionedModelEnpoint):
    endpoint = '/municipality'
    model = models.Municipality
    order_by = [model.insee]


@app.resource
class PostCode(VersionedModelEnpoint):
    endpoint = '/postcode'
    model = models.PostCode
    order_by = [model.code, model.municipality]
    filters = ['code', 'municipality']


@app.resource
class Group(VersionedModelEnpoint):
    endpoint = '/group'
    model = models.Group
    filters = ['municipality']


@app.resource
class HouseNumber(VersionedModelEnpoint):
    endpoint = '/housenumber'
    model = models.HouseNumber
    filters = ['parent', 'postcode', 'ancestors', 'group']
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
            # `serialize`), and CompoundSelect is hardcoded in peewee
            # SelectQuery, and we'd need to copy-paste code to be able to use
            # a custom CompoundQuery class instead.
            mask = self.get_collection_mask()
            qs = [h.serialize(mask) for h in qs.order_by(*self.order_by)]
        return qs

    filter_ancestors = filter_group = filter_ancestors_and_group

    def get_queryset(self):
        qs = super().get_queryset()
        bbox = get_bbox(request.args)
        if bbox:
            qs = (qs.join(models.Position)
                    .where(models.Position.center.in_bbox(**bbox))
                    .group_by(models.HouseNumber.pk)
                    .order_by(models.HouseNumber.pk))
        return qs


@app.resource
class Position(VersionedModelEnpoint):
    endpoint = '/position'
    model = models.Position
    filters = ['kind', 'housenumber']

    def get_queryset(self):
        qs = super().get_queryset()
        bbox = get_bbox(request.args)
        if bbox:
            qs = qs.where(models.Position.center.in_bbox(**bbox))
        return qs


@app.resource
class User(ModelEndpoint):
    endpoint = '/user'
    model = amodels.User


@app.route('/import/bal', methods=['POST'])
@auth.require_oauth()
def bal_post():
    """Import file at BAL format."""
    data = request.files['data']
    bal(StringIO(data.read().decode('utf-8-sig')))
    reporter = context.get('reporter')
    return dumps({'report': reporter})


@app.resource
class DiffEndpoint(CollectionEndpoint):
    endpoint = '/diff'
    model = versioning.Diff

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('', methods=['GET'])
    def get_collection(self):
        """Get database diffs.

        parameters:
        - name: increment
          in: query
          description: The minimal increment value to retrieve
          type: integer
          required: false
        responses:
          200:
            description: A list of diff objects
            schema:
              $ref: '#/definitions/Diff'
         """
        qs = versioning.Diff.select()
        try:
            increment = int(request.args.get('increment'))
        except ValueError:
            abort(400, error='Invalid value for increment')
        except TypeError:
            pass
        else:
            qs = qs.where(versioning.Diff.pk > increment)
        return self.collection(qs.serialize())


@app.route('/openapi', methods=['GET'])
def openapi():
    return dumps(app._schema)


app._schema.register_model(amodels.Session)
app._schema.register_model(versioning.Diff)
app._schema.register_model(versioning.Version)
app._schema.register_model(versioning.Flag)
