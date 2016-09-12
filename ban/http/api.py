from flask import Flask, request, make_response
from flask_restplus import Api, Resource, abort


from ban.core import models
from ban.core.encoder import dumps

app = Flask(__name__)
api = Api(app)


@api.representation('application/json')
def json(data, code, headers):
    resp = make_response(dumps(data), code)
    resp.headers.extend(headers)
    return resp


class Collection(Resource):

    filters = []

    def get(self):
        offset = request.args.get('offset', 20)
        limit = request.args.get('limit', 20) + offset
        qs = self.model.select()
        for key in self.filters:
            values = request.args.getlist(key)
            if values:
                field = getattr(self.model, key)
                values = list(map(field.coerce, values))
                qs = qs.where(field << values)
        count = qs.count()
        qs = qs.as_resource_list()[offset:limit]
        return {
            'collection': qs,
            'total': count,
        }


@api.route('/municipality/')
class MunicipalityCollection(Collection):
    model = models.Municipality


@api.route('/group/')
class GroupCollection(Collection):
    filters = ['municipality']
    model = models.Group


class CRUD(Resource):
    def get(self, identifier):
        inst = self.model.coerce(identifier)
        return inst.as_resource

    def post(self, identifier):
        instance = self.model.coerce(identifier)
        instance = self.save_object(instance, identifier)
        return instance.as_resource, 200

    def put(self, identifier):
        instance = self.model.coerce(identifier)
        instance = self.save_object(instance, identifier, update=False)
        headers = {'Location': api.url_for(self, identifier=instance.id)}
        return instance.as_resource, 201, headers

    def save_object(self, instance=None, identifier=None, update=True):
        validator = self.model.validator(update=update, instance=instance,
                                         **request.json)
        if validator.errors:
            abort(422, **validator.errors)
        try:
            instance = validator.save()
        except models.Model.ForcedVersionError as e:
            abort(409, str(e))
        return instance


@api.route('/municipality/<string:identifier>/')
class Municipality(CRUD):
    model = models.Municipality


@api.route('/group/<string:identifier>/')
class Group(CRUD):
    model = models.Group


if __name__ == '__main__':
    app.run(debug=True)
