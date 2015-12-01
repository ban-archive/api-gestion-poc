from falcon.response import Response as BaseResponse

from ban.core.encoder import dumps


class Response(BaseResponse):

    def json(self, **kwargs):
        self.body = dumps(kwargs)
