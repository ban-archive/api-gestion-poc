import falcon

from .request import Request
from .response import Response
from . import middlewares
from .routing import Router


application = app = falcon.API(
    middleware=[
        middlewares.CorsMiddleware(),
        middlewares.SessionMiddleware(),
    ],
    response_type=Response,
    request_type=Request,
    router=Router(),
)
