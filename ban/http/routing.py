import re

from falcon import HTTP_METHODS, HTTP_404
from falcon.responders import create_default_options, create_method_not_allowed
from falcon.routing import DefaultRouter

from ban import __version__


class Router(DefaultRouter):

    def __init__(self, *args, **kwargs):
        self._index = {}
        self.endpoints = {}
        reverse.attach_router(self)
        super().__init__(*args, **kwargs)

    def find(self, uri):
        if uri == '/':
            return (self, {'GET': self.on_get}, {})
        return super().find(uri)

    def reverse(self, name, **params):
        if not isinstance(name, str):
            name = self.cls_name(name)
        if 'id' in params:
            params['identifier'] = '{identifier}:{id}'.format(**params)
            del params['id']
        return self._index[name].format(**params)

    def cls_name(self, cls):
        return re.sub("([a-z])([A-Z])", "\g<1>-\g<2>", cls.__name__).lower()

    def index(self, name, template):
        if name in self._index and self._index[name] != template:
            raise ValueError('{} already in {}'.format(name, self._index))
        self._index[name] = template

    def register_route(self, api):
        api.add_route('/help', self)

    def get_responder_help(self, responder, resource):
        return (responder.__doc__ or '').format(
                                        resource=resource.__class__.__name__)

    def register_endpoint(self, path, method_map, resource):
        self.endpoints[path] = {verb: self.get_responder_help(func, resource)
                                for verb, func in method_map.items()
                                if hasattr(func, '_path')}  # Not 405 attached.
        self.add_route(path, method_map, resource)

    def register_resource(self, resource):
        base = self.cls_name(resource.__class__)
        paths = {}
        for attr in dir(resource):
            # Keep supporting default "on_VERB" format for simple cases.
            if attr.startswith('on_'):
                method = getattr(resource.__class__, attr)
                if not hasattr(method, '_path'):
                    _, verb, *path = method.__name__.split('_')
                    path = '/'.join(path)
                    if path:
                        path = '/' + path
                    setattr(method, '_path', path)
                    method._verb = verb
                    method._name = '-'.join(path)
            responder = getattr(resource, attr)
            if hasattr(responder, '_path'):
                path = '/{}{}'.format(base, responder._path)
                name_els = [base]
                if responder._name:
                    name_els.append(responder._name)
                name = '-'.join(name_els)
                self.index(name, path)
                if path not in paths:
                    paths[path] = {}
                verb = responder._verb
                paths[path][verb.upper()] = responder
        for path, method_map in paths.items():
            # See https://github.com/falconry/falcon/issues/667
            allowed_methods = sorted(list(method_map.keys()))
            if 'OPTIONS' not in method_map:
                responder = create_default_options(allowed_methods)
                allowed_methods.append('OPTIONS')
            responder = create_method_not_allowed(allowed_methods)
            for method in HTTP_METHODS:
                if method not in allowed_methods:
                    method_map[method] = responder

            self.register_endpoint(path, method_map, resource)

    @property
    def help(self):
        return {
            'contact': 'contact@ban.somewhere.fr',
            'licence': 'XXXX',
            'doc_url': 'https://doc.ban.somewhere.fr',
            'version': __version__,
            'endpoints': self.endpoints
        }

    def on_get(self, req, resp, **params):
        if not req.path == '/help':
            resp.status = HTTP_404
        resp.json(**self.help)

    def on_get_endpoint_help(self, req, resp, responder, resource, **params):
        resp.json(help=self.get_responder_help(responder, resource))


class Reverse:

    def __call__(self, name, **params):
        return self.router.reverse(name, **params)

    def attach_router(self, router):
        self.router = router


reverse = Reverse()
