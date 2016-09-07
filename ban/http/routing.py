from falcon import HTTP_METHODS, HTTP_404
from falcon.responders import create_default_options, create_method_not_allowed
from falcon.routing import DefaultRouter


class Router(DefaultRouter):

    def __init__(self, *args, **kwargs):
        self._index = {}
        self.endpoints = {}
        reverse.attach_router(self)
        super().__init__(*args, **kwargs)

    def reverse(self, name, **params):
        if not isinstance(name, str):
            # Allow to pass in a class.
            name = self.cls_name(name)
        if 'id' in params:
            params['identifier'] = '{identifier}:{id}'.format(**params)
            del params['id']
        return self._index[name].format(**params)

    def cls_name(self, cls):
        return cls.__name__.lower()

    def index(self, name, template):
        if name in self._index:
            if self._index[name] != template:
                raise ValueError('{} already in {}'.format(name, self._index))
        else:
            self._index[name] = template

    def attach_reverse(self, name, suffix, resource):
        """Allow to call resource.name_uri for convenience."""
        method_name = '{}_uri'.format(suffix.replace('-', '_'))
        setattr(resource, method_name,
                lambda s, r, i: self.attached_reverse(name, r, i))

    def attached_reverse(self, name, req, instance):
        return 'https://{}{}'.format(req.host,
                                     reverse(name, identifier=instance.id))

    def register_route(self, api):
        api.add_route('/schema', self)

    def extend_method_map(self, method_map):
        # See https://github.com/falconry/falcon/issues/667
        allowed_methods = sorted(list(method_map.keys()))
        if 'OPTIONS' not in method_map:
            responder = create_default_options(allowed_methods)
            allowed_methods.append('OPTIONS')
        responder = create_method_not_allowed(allowed_methods)
        for method in HTTP_METHODS:
            if method not in allowed_methods:
                method_map[method] = responder

    def register_resource(self, resource):
        base = self.cls_name(resource.__class__)
        paths = {}
        for attr in dir(resource):
            responder = getattr(resource, attr)
            if hasattr(responder, '_path'):
                path = '/{}{}'.format(base, responder._path)
                name_els = [base]
                suffix = responder._suffix
                if suffix:
                    name_els.append(suffix)
                else:
                    # Only for attached reverse, not for name
                    suffix = 'root'
                name = '-'.join(name_els)
                self.index(name, path)
                self.attach_reverse(name, suffix, resource.__class__)
                if path not in paths:
                    paths[path] = {}
                verb = responder._verb
                paths[path][verb.upper()] = responder
        for path, method_map in paths.items():
            self.extend_method_map(method_map)
            self.add_route(path, method_map, resource)
            self.schema.register_endpoint(path, method_map, resource)

    def on_get(self, req, resp, **params):
        if not req.path == '/schema':
            resp.status = HTTP_404
        resp.json(**self.schema)


class Reverse:

    def __call__(self, name, **params):
        return self.router.reverse(name, **params)

    def attach_router(self, router):
        self.router = router


reverse = Reverse()
