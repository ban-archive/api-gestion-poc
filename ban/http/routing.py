from falcon.routing import DefaultRouter


class Router(DefaultRouter):
    # Use me when https://github.com/falconry/falcon/pull/652 get merged.

    def __init__(self, *args, **kwargs):
        self._index = {}
        url.attach_router(self)
        super().__init__(*args, **kwargs)

    def add_route(self, name, uri_template, method_map, resource):
        self._index[name] = uri_template
        super().add_route(uri_template, method_map, resource)

    def reverse(self, name, **params):
        return self._index[name].format(**params)


class URL:

    def __call__(self, name, **params):
        return self.router.reverse(name, **params)

    def attach_router(self, router):
        self.router = router


url = URL()
