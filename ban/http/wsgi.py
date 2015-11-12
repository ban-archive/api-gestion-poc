import falcon

from .request import Request
from .response import Response
from . import middlewares


application = app = falcon.API(
    middleware=[
        middlewares.CorsMiddleware(), middlewares.ValidationMiddleware(),
        middlewares.SessionMiddleware(),
    ],
    response_type=Response,
    request_type=Request
)
