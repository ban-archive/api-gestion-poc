from io import StringIO
from urllib.parse import urlencode

import peewee
from flask import request, url_for
import psycopg2

from ban.auth import models as amodels
from ban.commands.bal import bal
from ban.core import context, models, versioning, config
from ban.core.encoder import dumps
from ban.core.exceptions import (IsDeletedError, MultipleRedirectsError,
                                 RedirectError, ResourceLinkedError)
from ban.http.auth import auth
from ban.http.wsgi import app
from ban.utils import parse_mask

from .utils import abort, get_bbox, link, get_search_params


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

    def save_object(self, instance=None, update=False, json=None):
        validator = self.model.validator(update=update, instance=instance,
                                         **json or {})
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
                if values == [None]:
                    qs = qs.where(field.is_null())
                else:
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

    @app.jsonify
    @app.endpoint(methods=['GET'])
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
            401:
                $ref: '#/responses/401'
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
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
            410:
                $ref: '#/responses/410'
        """
        instance = self.get_object(identifier)
        status = 410 if instance.deleted_at else 200
        try:
            return instance.serialize(self.get_mask()), status
        except ValueError as e:
            abort(400, error=str(e))

    @app.jsonify
    @app.endpoint('/<identifier>', methods=['POST'])
    def post_resource(self, identifier, json=None):
        """Post {resource} with 'identifier'.

        parameters:
            - $ref: '#/parameters/identifier'
            - name: body
              in: body
              schema:
                $ref: '#/definitions/{resource}'
              required: true
              description:
                {resource} object that needs to be updated to the BAN.
        responses:
            200:
                description: Instance has been successfully updated.
                schema:
                    $ref: '#/definitions/{resource}'
            400:
                $ref: '#/responses/400'
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                $ref: '#/responses/410'
            422:
                $ref: '#/responses/422'
        """
        if not json:
            json = request.json
        instance = self.get_object(identifier)
        instance = self.save_object(instance, update=True, json=json)
        return instance.as_resource, 200

    @app.jsonify
    @app.endpoint(methods=['POST'])
    def post(self, json=None):
        """Create {resource}.

        parameters:
            - name: body
              in: body
              schema:
                $ref: '#/definitions/{resource}'
              required: true
              description:
                {resource} object that needs to be added to the BAN.
        responses:
            201:
                description: Instance has been successfully created.
                schema:
                    $ref: '#/definitions/{resource}'
            400:
                $ref: '#/responses/400'
            401:
                $ref: '#/responses/401'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                $ref: '#/responses/410'
            422:
                $ref: '#/responses/422'
        """
        if not json:
            json = request.json
        instance = self.save_object(json=json)
        endpoint = '{}-get-resource'.format(self.__class__.__name__.lower())
        headers = {'Location': url_for(endpoint, identifier=instance.id)}
        return instance.as_resource, 201, headers

    @app.jsonify
    @app.endpoint('/<identifier>', methods=['PATCH'])
    def patch(self, identifier, json=None):
        """Patch {resource} with 'identifier'.

        parameters:
            - $ref: '#/parameters/identifier'
            - name: body
              in: body
              schema:
                $ref: '#/definitions/{resource}'
              required: true
              description:
                {resource} object that need to be patched to the BAN.
        responses:
            200:
                description: Instance has been updated successfully.
                schema:
                    $ref: '#/definitions/{resource}'
            400:
                $ref: '#/responses/400'
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                $ref: '#/responses/410'
            422:
                $ref: '#/responses/422'
        """
        if not json:
            json = request.json
        instance = self.get_object(identifier)
        instance = self.save_object(instance, update=True, json=json)
        return instance.as_resource, 200

    @app.jsonify
    @app.endpoint('/<identifier>', methods=['PUT'])
    def put(self, identifier, json=None):
        """Replace or restore {resource} with 'identifier'.

        parameters:
            - $ref: '#/parameters/identifier'
            - name: body
              in: body
              schema:
                $ref: '#/definitions/{resource}'
              required: true
              description:
                {resource} object that needs to be replaced to the BAN
        responses:
            200:
                description: Instance has been successfully replaced.
                schema:
                    $ref: '#/definitions/{resource}'
            400:
                $ref: '#/responses/400'
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                $ref: '#/responses/410'
            422:
                $ref: '#/responses/422'
        """
        if not json:
            json = request.json
        instance = self.get_object(identifier)
        if instance.deleted_at:
            # We want to create only one new version for a restore. Change the
            # property here, but let the save_object do the actual save
            # if the data is valid.
            instance.deleted_at = None
        instance = self.save_object(instance, json=json)
        return instance.as_resource, 200

    @app.jsonify
    @app.endpoint('/<identifier>', methods=['DELETE'])
    def delete(self, identifier):
        """Delete {resource} with 'identifier'.

        parameters:
            - $ref: '#/parameters/identifier'
        responses:
            204:
                description: Instance has been deleted successfully.
                schema:
                    $ref: '#/definitions/{resource}'
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
            409:
                description: Conflict.
                schema:
                    $ref: '#/definitions/{resource}'
            410:
                $ref: '#/responses/410'
        """
        instance = self.get_object(identifier)
        try:
            instance.mark_deleted()
        except ResourceLinkedError as e:
            abort(409, error=str(e))
        return instance.as_resource, 204


class VersionedModelEndpoint(ModelEndpoint):
    @app.jsonify
    @app.endpoint('/<identifier>/versions', methods=['GET'])
    def get_versions(self, identifier):
        """Get {resource} versions.

        parameters:
            - $ref: '#/parameters/identifier'
        responses:
            200:
                description: Version collection for resource {resource}.
                schema:
                    type: object
                    properties:
                        collection:
                            type: array
                            items:
                                $ref: '#/definitions/Version'
                        total:
                            name: total
                            type: integer
                            description: total resources available
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
        """
        instance = self.get_object(identifier)
        return self.collection(instance.versions.serialize())

    @app.jsonify
    @app.endpoint('/<identifier>/versions/<datetime:ref>',
                  '/<identifier>/versions/<int:ref>', methods=['GET'])
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
            400:
                $ref: '#/responses/400'
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
        """
        instance = self.get_object(identifier)
        version = instance.load_version(ref)
        if not version:
            abort(404, error='Version reference `{}` not found'.format(ref))
        return version.serialize()

    @app.jsonify
    @app.endpoint('/<identifier>/versions/<int:ref>/flag', methods=['POST'])
    def post_version(self, identifier, ref):
        """Flag a {resource} version.

        parameters:
            - $ref: '#/parameters/identifier'
            - name: ref
              in: path
              type: integer
              required: true
              description: version reference, either a date or an increment.
            - name: status
              in: query
              type: string
              required: true
              description:
                A status boolean key (= true to flag, false to unflag).
        responses:
            200:
                description: version flag was updated.
            400:
                $ref: '#/responses/400'
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
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
    @app.endpoint('/<identifier>/redirects/<old>', methods=['PUT'])
    def put_redirects(self, identifier, old):
        """Create a new redirect to this {resource}.

        parameters:
            - $ref: '#/parameters/identifier'
            - name: old
              in: path
              type: string
              required: true
              description: Old {resource} identifier:value
        responses:
            201:
                description: redirect was successfully created.
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
            422:
                description: error while creating the redirect.
        """
        instance = self.get_object(identifier)
        old_identifier, old_value = old.split(':')
        try:
            versioning.Redirect.add(instance, old_identifier, old_value)
        except ValueError as e:
            abort(422, error=str(e))
        return '', 201


    @auth.require_oauth()
    @app.endpoint('/<identifier>/redirects/<old>', methods=['DELETE'])
    def delete_redirects(self, identifier, old):
        """Delete a redirect to this {resource}

        parameters:
            - $ref: '#/parameters/identifier'
            - name: old
              in: path
              type: string
              required: true
              description: old {resource} identifier:value
        responses:
            204:
                description: redirect was successfully deleted.
            401:
                $ref: '#/responses/401'
            404:
                $ref: '#/responses/404'
        """
        instance = self.get_object(identifier)
        old_identifier, old_value = old.split(':')
        versioning.Redirect.remove(instance, old_identifier, old_value)
        return '', 204

    @auth.require_oauth()
    @app.jsonify
    @app.endpoint('/<identifier>/redirects', methods=['GET'])
    def get_redirects(self, identifier):
        """Get a collection of Redirect pointing to this {resource}.

            parameters:
                - $ref: '#/parameters/identifier'
            responses:
                200:
                    description: A list of redirects (identifier:value)
                    schema:
                        type: object
                        properties:
                            collection:
                                type: array
                                items:
                                    $ref: '#/definitions/Redirect'
                            total:
                                name: total
                                type: integer
                                description: total resources available
                401:
                    $ref: '#/responses/401'
                404:
                    $ref: '#/responses/404'
        """
        instance = self.get_object(identifier)
        cls = versioning.Redirect
        qs = cls.select().where(cls.model_id == instance.id)
        return self.collection(qs.serialize())


@app.resource
class Municipality(VersionedModelEndpoint):
    endpoint = '/municipality'
    model = models.Municipality
    order_by = [model.insee]

    def get_queryset(self):
        qs = super().get_queryset()
        search_params = get_search_params(request.args)
        if search_params['search'] is not None:
            qs = (qs.where(models.Municipality.name.search(**search_params)))
        return qs


@app.resource
class PostCode(VersionedModelEndpoint):
    endpoint = '/postcode'
    model = models.PostCode
    order_by = [model.code, model.municipality]
    filters = ['code', 'municipality']

    def get_queryset(self):
        qs = super().get_queryset()
        search_params = get_search_params(request.args)
        if search_params['search'] is not None:
            qs = (qs.where(models.PostCode.name.search(**search_params)))
        return qs


@app.resource
class Group(VersionedModelEndpoint):
    endpoint = '/group'
    model = models.Group
    filters = ['municipality']

    def get_queryset(self):
        qs = super().get_queryset()
        search_params = get_search_params(request.args)
        if search_params['search'] is not None:
            qs = (qs.where(models.Group.name.search(**search_params)))
        return qs


@app.resource
class HouseNumber(VersionedModelEndpoint):
    endpoint = '/housenumber'
    model = models.HouseNumber
    filters = ['number','ordinal', 'parent', 'postcode', 'ancestors', 'group']
    order_by = [peewee.SQL('number ASC NULLS FIRST'),
                peewee.SQL('ordinal ASC NULLS FIRST')]


    def filter_group(self, qs):
        values = request.args.getlist('group')
        if values:
            field = getattr(self.model, 'parent')
            try:
                values = list(map(field.coerce, values))
            except ValueError:
                abort(400, error='Invalid value for filter {}'.format('group'))
            except peewee.DoesNotExist:
                # Return an empty collection as the fk is not found.
                return None
            qs = qs.where(field << values)
            return qs

    def filter_ancestors(self, qs):
        # ancestors is a m2m so we cannot use the basic filtering
        # from self.filters.
        ancestors = request.args.getlist('ancestors')
        values = list(map(self.model.ancestors.coerce, ancestors))
        if values:
            m2m = self.model.ancestors.get_through_model()
            qs = (qs.join(m2m, on=(m2m.housenumber == self.model.pk)))
            # We evaluate the qs ourselves here, because it's a CompoundSelect
            # that does not know about our SelectQuery custom methods (like
            # `serialize`), and CompoundSelect is hardcoded in peewee
            # SelectQuery, and we'd need to copy-paste code to be able to use
            # a custom CompoundQuery class instead.
        mask = self.get_collection_mask()
        qs = [h.serialize(mask) for h in qs.order_by(*self.order_by)]
        return qs

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
class Position(VersionedModelEndpoint):
    endpoint = '/position'
    model = models.Position
    filters = ['kind', 'housenumber']

    def get_queryset(self):
        qs = super().get_queryset()
        bbox = get_bbox(request.args)
        if bbox:
            qs = qs.where(models.Position.center.in_bbox(**bbox))
        return qs


@app.route('/import/bal', methods=['POST'])
@auth.require_oauth('bal')
def bal_post():
    """Import file at BAL format."""
    data = request.files['data']
    bal(StringIO(data.read().decode('utf-8-sig')))
    reporter = context.get('reporter')
    return dumps({'report': reporter})


@app.route('/batch', methods=['POST'])
@auth.require_oauth()
def batch():
    """
    Execute multiple requests, submitted as a batch.
    :statuscode 207: Multi status
    """
    try:
        req = request.json
        if req == []:
            raise ValueError
    except ValueError as e:
        abort(400, error=str(e))
    db = models.Municipality._meta.database
    with db.atomic():
        for index, re in enumerate(req):
            method = re.get('method')
            if method is None:
                abort(422, error="No method given")
            path = re.get('path')
            if path is None:
                abort(422, error="No path given")
            body = re.get('body') or {}
            if body == {} and method != 'DELETE':
                abort(422, error='No body given')
            if path[:13] == Municipality.endpoint:
                self = Municipality()
            elif path[:9] == PostCode.endpoint:
                self = PostCode()
            elif path[:6] == Group.endpoint:
                self = Group()
            elif path[:12] == HouseNumber.endpoint:
                self = HouseNumber()
            elif path[:9] == Position.endpoint:
                self = Position()
            else:
                abort(422, error="Wrong resource {}".format(path))
            scopes = '{}_write'.format(self.__class__.__name__.lower())
            if scopes not in request.oauth.access_token.scopes:
                abort(401)
            if method == 'POST':
                rep = self.post(json=body)
            elif method == 'PUT':
                identifier = path.split('/')[2]
                rep = self.put(identifier=identifier, json=body)
            elif method == 'PATCH':
                identifier = path.split('/')[2]
                rep = self.patch(identifier=identifier, json=body)
            elif method == 'DELETE':
                identifier = path.split('/')[2]
                rep = self.delete(identifier=identifier)
            else:
                abort(422, error="Wrong request {}".format(method))
    return rep


@app.resource
class Diff(CollectionEndpoint):
    endpoint = '/diff'
    model = versioning.Diff

    @app.jsonify
    @app.endpoint('', methods=['GET'])
    def get_collection(self):
        """Get database diffs.

        parameters:
            - name: increment
              in: query
              type: integer
              required: false
              description: The minimal increment value to retrieve
        responses:
            200:
                description: A list of diff objects
                schema:
                    type: object
                    properties:
                        total:
                            name: total
                            type: integer
                            description: total resources available
                        collection:
                            name: collection
                            type: array
                            items:
                                $ref: '#/definitions/Diff'
            400:
                $ref: '#/responses/400'
            401:
                $ref: '#/responses/401'
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

@app.route('/bbox', methods=['GET'])
@auth.require_oauth()
@app.jsonify
def bbox():
    limit = min(int(request.args.get('limit', CollectionEndpoint.DEFAULT_LIMIT)), CollectionEndpoint.MAX_LIMIT)
    bbox = get_bbox(request.args)
    unique = request.args.get('unique')

    dbname = config.DB_NAME
    user = config.get('DB_USER')
    password = config.get('DB_PASSWORD')
    host = config.get('DB_HOST')
    if (host is None):
        host = "localhost"
    port = config.get('DB_PORT')

    connectString = "dbname='{}' user='{}' password='{}' host='{}' port='{}'".format(dbname,user,password,host,port)
    conn = psycopg2.connect(connectString)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if unique == 'true':
        cur.execute(
            """SELECT count(distinct housenumber_id) FROM position WHERE center && ST_MakeEnvelope(%(west)s, %(south)s, %(east)s, %(north)s)""",
            {
                "west": bbox["west"],
                "south": bbox["south"],
                "east": bbox["east"],
                "north": bbox["north"]
            }
        )
        response = {"collection": [], "total": cur.fetchone()["count"]}
        cur.execute(
            """SELECT
                p.id as pos_id, p.name as pos_name, st_x(center) as pos_x, st_y(center) as pos_y, p.kind as pos_kind, p.positioning as pos_positioning, p.source as pos_source, p.source_kind as pos_source_kind, p.version as pos_version,
                h.id as hn_id, h.number as hn_number, h.ordinal as hn_ordinal, h.version as hn_version, 
                po.id as post_id, po.name as post_name, po.code as post_code,
                g.id as group_id, g.addressing as group_addressing, g.alias as group_alias, g.fantoir as group_fantoir, g.ign as group_ign, g.kind as group_kind, g.laposte as group_laposte, g.name as group_name
                FROM position as p 
                LEFT JOIN housenumber as h 
                on (h.pk = p.housenumber_id) 
                LEFT JOIN "group" as g 
                on (h.parent_id = g.pk) 
                LEFT JOIN postcode as po 
                on (h.postcode_id = po.pk) 
                WHERE center && ST_MakeEnvelope(%(west)s, %(south)s, %(east)s, %(north)s)
                AND p.deleted_at is null AND h.deleted_at is null and g.deleted_at is null
                AND p.modified_at = (select max(modified_at) from position where housenumber_id=h.pk)
                limit %(limit)s""",
            {
                "limit": limit,
                "west": bbox["west"],
                "south": bbox["south"],
                "east": bbox["east"],
                "north": bbox["north"]
            })
    else:
        cur.execute(
            """SELECT count(*) FROM position WHERE center && ST_MakeEnvelope(%(west)s, %(south)s, %(east)s, %(north)s)""",
            {
                "west": bbox["west"],
                "south": bbox["south"],
                "east": bbox["east"],
                "north": bbox["north"]
            }
        )
        response = {"collection": [], "total": cur.fetchone()["count"]}
        cur.execute(
            """SELECT
                p.id as pos_id, p.name as pos_name, st_x(center) as pos_x, st_y(center) as pos_y, p.kind as pos_kind, p.positioning as pos_positioning, p.source as pos_source, p.source_kind as pos_source_kind, p.version as pos_version,
                h.id as hn_id, h.number as hn_number, h.ordinal as hn_ordinal, h.version as hn_version, 
                po.id as post_id, po.name as post_name, po.code as post_code,
                g.id as group_id, g.addressing as group_addressing, g.alias as group_alias, g.fantoir as group_fantoir, g.ign as group_ign, g.kind as group_kind, g.laposte as group_laposte, g.name as group_name
                FROM position as p 
                LEFT JOIN housenumber as h 
                on (h.pk = p.housenumber_id) 
                LEFT JOIN "group" as g 
                on (h.parent_id = g.pk) 
                LEFT JOIN postcode as po 
                on (h.postcode_id = po.pk) 
                WHERE center && ST_MakeEnvelope(%(west)s, %(south)s, %(east)s, %(north)s)
                AND p.deleted_at is null AND h.deleted_at is null and g.deleted_at is null
                limit %(limit)s""",
            {
                "limit": limit,
                "west": bbox["west"],
                "south": bbox["south"],
                "east": bbox["east"],
                "north": bbox["north"]
            })

    for row in cur:
        occ = {
            "id": row["pos_id"],
            "name": row["pos_name"],
            "center": {
                "type": "Point",
                "coordinates": [row["pos_x"], row["pos_y"]]
            },
            "kind": row["pos_kind"],
            "positioning": row["pos_positioning"],
            "source": row["pos_source"],
            "source_kind": row["pos_source_kind"],
            "version": row["pos_version"],
            "housenumber": {
                "id": row["hn_id"],
                "number": row["hn_number"],
                "ordinal": row["hn_ordinal"],
                "postcode": {
                    "id": row["post_id"],
                    "name": row["post_name"],
                    "code": row["post_code"]
                },
                "group": {
                    "id": row["group_id"],
                    "addressing": row["group_addressing"],
                    "alias": row["group_alias"],
                    "fantoir": row["group_fantoir"],
                    "ign": row["group_ign"],
                    "kind": row["group_kind"],
                    "laposte": row["group_laposte"],
                    "name": row["group_name"]
                },
                "version":row["hn_version"]
            }
        }
        response["collection"].append(occ)

    return response

@app.route('/openapi', methods=['GET'])
@app.jsonify
def openapi():
    return app._schema


app._schema.register_model(amodels.Session)
app._schema.register_model(versioning.Diff)
app._schema.register_model(versioning.Version)
app._schema.register_model(versioning.Flag)
app._schema.register_model(versioning.Redirect)
