import json
from datetime import datetime

from falcon.response import Response as BaseResponse


class ResourceEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        try:
            return super().default(o)
        except TypeError:
            return str(o)


class Response(BaseResponse):

    def json(self, **kwargs):
        self.body = json.dumps(kwargs, cls=ResourceEncoder)
