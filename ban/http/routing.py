import re
from string import Formatter

from falcon.routing import DefaultRouter


class Router(DefaultRouter):

    def __init__(self, *args, **kwargs):
        self._index = {}
        reverse.attach_router(self)
        self.formatter = Formatter()
        super().__init__(*args, **kwargs)

    def add_route(self, uri_template, method_map, resource):
        self.index(uri_template, resource)
        super().add_route(uri_template, method_map, resource)

    def reverse(self, name, **params):
        if not isinstance(name, str):
            name = self.cls_name(name)
        if 'identifier' in params:
            params['id'] = '{identifier}:{id}'.format(**params)
            del params['identifier']
        len_ = len(params)
        return self._index[name][len_].format(**params)

    def cls_name(self, cls):
        return re.sub("([a-z])([A-Z])", "\g<1>-\g<2>", cls.__name__).lower()

    def index(self, template, resource):
        # We want only one name by endpoint, and let the url reverse define
        # which suburl to be used according to the number of passed kwargs.
        # See https://docs.python.org/3.4/library/string.html#string.Formatter.
        len_ = len([x for x in self.formatter.parse(template) if x[1]])
        name = self.cls_name(resource.__class__)
        if name not in self._index:
            self._index[name] = {}
        self._index[name][len_] = template


class Reverse:

    def __call__(self, name, **params):
        return self.router.reverse(name, **params)

    def attach_router(self, router):
        self.router = router


reverse = Reverse()
