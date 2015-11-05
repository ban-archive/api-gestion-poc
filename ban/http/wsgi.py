import falcon

from .request import Request
from .response import Response
from .middlewares import CorsMiddleware, ValidationMiddleware


application = app = falcon.API(
    middleware=[CorsMiddleware(), ValidationMiddleware()],
    response_type=Response,
    request_type=Request
)
