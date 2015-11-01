import json

from falcon.request import Request as BaseRequest


class Request(BaseRequest):

    @property
    def json(self, **kwargs):
        if self.content_length in (None, 0):
            return
        if not hasattr(self, '_json'):
            self._json = json.loads(self.stream.read().decode())
        return self._json
