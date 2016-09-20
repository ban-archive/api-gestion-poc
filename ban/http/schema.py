import yaml

from ban import __version__


BASE = {
    'info': {
        'title': 'Api de gestion de la Base adresse nationale',
        'contact': {
            'name': 'Equipe support',
            'email': 'contact@ban.somewhere.fr',
        },
        'license': {
            'name': 'XXXX',
            'url': 'http://xxxx.org',
        },
        'version': __version__,
    },
    'swagger': '2.0',
    'schemes': ['https'],
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'externalDocs': {
        'url': 'https://adresse.data.gouv.fr/api-gestion/',
    },
    'paths': {},
    'definitions': {
        'Error': {
            'properties': {
                'title': {
                    'type': 'string',
                    'description': 'Summary of the error'
                },
                'description': {
                    'type': 'string',
                    'description': 'Description of the error'
                },
            }
        }
    },
    'parameters': {
        'identifier': {
            'name': 'identifier',
            'in': 'path',
            'type': 'string',
            'required': True,
        }
    }
}


class Schema(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(BASE)

    def get_responder_summary(self, responder, resource):
        return (responder.__doc__ or '').split('\n\n')[0].format(
            resource=resource.__class__.__name__)

    def get_responder_doc(self, func, resource):
        default = {
            'summary': self.get_responder_summary(func, resource),
        }
        try:
            doc = (func.__doc__ or '').split('\n\n')[1]
        except IndexError:
            pass
        else:
            try:
                extra = yaml.load(doc.format(
                    resource=resource.__class__.__name__))
            except ValueError:
                pass
            else:
                default.update(extra)
        return default

    def register_model(self, model):
        if hasattr(model, 'definition'):
            definition = yaml.load(model.definition)
        elif hasattr(model, 'jsonschema'):
            definition = {
                'properties': {name: self.field_definition(name, field)
                               for name, field
                               in model.jsonschema['properties'].items()}
            }
        else:
            definition = None
        if definition:
            self['definitions'][model.__name__] = definition

    def field_definition(self, name, schema):
        definition = {}
        type_ = schema.get('type')
        if isinstance(type_, list):
            type_ = type_[0]
        if type_ == 'integer':
            definition['type'] = 'integer'
        elif type_ == 'datetime':
            definition['type'] = 'string'
            definition['format'] = 'date-time'
        elif type_ == 'array':
            definition['type'] = 'array'
            # Try to guess if it's a m2m field.
            if 'field' in schema:
                field = schema['field']
                if hasattr(field, 'rel_model'):
                    definition['items'] = {
                        '$ref': '#/definitions/{}'.format(
                            field.rel_model.__name__)
                    }
                else:
                    definition['items'] = {
                        'type': field.db_field
                    }
            elif 'model' in schema:
                definition['items'] = {
                    '$ref': '#/definitions/{}'.format(schema['model'])
                }
        elif type_ == 'object':
            definition['type'] = 'object'
        elif type_ == 'point':
            definition['type'] = 'object'
            definition['format'] = 'geo'
        elif type_ == 'foreignkey':
            definition['$ref'] = '#/definitions/{}'.format(
                schema['field'].rel_model.__name__)
        else:
            definition['type'] = 'string'
        return definition

    def register_endpoint(self, path, func, methods, endpoint):
        definition = {verb.lower(): self.get_responder_doc(func, endpoint)
                      for verb in methods}
        if path in self['paths']:
            self['paths'][path].update(definition)
        else:
            self['paths'][path] = definition
