import falcon

from .request import Request
from .response import Response
from . import middlewares
from .routing import Router


class API(falcon.API):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._router.register_route(self)

    def register_resource(self, resource):
        self._router.register_resource(resource)

    def endpoint(self, path='', verb=None, suffix=None):
        """Override default endpoint path and verb."""

        def wrapped(func):
            _, autoverb, *extra = func.__name__.split('_')
            func._path = path
            func._suffix = suffix if suffix is not None else '-'.join(extra)
            func._verb = verb or autoverb
            return func

        return wrapped

    def _get_responder(self, req):
        responder, params, resource = super()._get_responder(req)
        if responder == falcon.responders.path_not_found:
            # See https://github.com/falconry/falcon/issues/668
            responder = self._router.on_get
        elif req.query_string == 'help':
            params['responder'] = responder
            params['resource'] = resource
            responder = self._router.on_get_endpoint_help
        return responder, params, resource


application = app = API(
    middleware=[
        middlewares.CorsMiddleware(),
        middlewares.SessionMiddleware(),
    ],
    response_type=Response,
    request_type=Request,
    router=Router(),
)
