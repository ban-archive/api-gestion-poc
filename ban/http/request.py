import json

from falcon.request import Request as BaseRequest
from falcon.errors import HTTPInvalidParam


class Request(BaseRequest):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if (self.content_type is not None and
                'application/json' in self.content_type):
            self._parse_form_jsonencoded()

    @property
    def json(self, **kwargs):
        if self.content_length in (None, 0):
            return
        if not hasattr(self, '_json'):
            # When consuming body for urlencoded form parsing, Falcon does not
            # reset it.
            # See https://github.com/falconry/falcon/pull/649.
            self.stream.seek(0)
            self._json = json.loads(self.stream.read().decode())
        return self._json

    def _parse_form_jsonencoded(self):
        body = self.stream.read().decode()
        self.stream.seek(0)
        if body:
            extra_params = json.loads(body)
            self._params.update(extra_params)

    def get_param_as_float(self, name, required=False, store=None):
        try:
            val = float(self.get_param(name, required=required))
        except ValueError:
            msg = 'The value cannot be cast as float.'
            raise HTTPInvalidParam(msg, name)
        except TypeError:
            # None value, but not required otherwise it would have raised on
            # get_param.
            pass
        else:
            if store is not None:
                store[name] = val
            return val
