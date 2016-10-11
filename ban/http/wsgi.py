import re
from functools import wraps
from datetime import timezone
from dateutil.parser import parse as parse_date

from flask import Flask, make_response
from flask_cors import CORS
from werkzeug.routing import BaseConverter, ValidationError

from .schema import Schema
from ban.core.encoder import dumps


class App(Flask):
    _schema = Schema()

    def jsonify(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            rv = func(*args, **kwargs)
            if not isinstance(rv, tuple):
                rv = [rv]
            else:
                rv = list(rv)
            rv[0] = dumps(rv[0])
            resp = make_response(tuple(rv))
            resp.mimetype = 'application/json'
            return resp
        return wrapper

    def endpoint(self, path='/', **kwargs):
        def wrapper(func):
            if not hasattr(func, '_endpoints'):
                func._endpoints = []
            func._endpoints.append((path, kwargs))
            return func
        return wrapper

    def resource(self, cls):
        if hasattr(cls, 'model'):
            self._schema.register_model(cls.model)
        instance = cls()
        for name in dir(cls):
            func = getattr(instance, name)
            if hasattr(func, '_endpoints'):
                self.register_endpoints(func)
        return cls

    def register_endpoints(self, func):
        cls = func.__self__.__class__
        for endpoint in func._endpoints:
            path, kwargs = endpoint
            path = '{}{}'.format(cls.endpoint, path)
            endpoint = ('{}-{}'.format(cls.__name__, func.__name__)
                               .lower().replace('_', '-'))
            self.add_url_rule(path, view_func=func, endpoint=endpoint,
                              strict_slashes=False, **kwargs)
            path = re.sub(r'<(\w+:)?(\w+)>', r'{\2}', path)
            self._schema.register_endpoint(path, func, kwargs['methods'], cls)


class DateTimeConverter(BaseConverter):

    def to_python(self, value):
        try:
            value = parse_date(value)
        except ValueError:
            raise ValidationError
        # Be smart, imply that naive dt are in the same tz the API
        # exposes, which is UTC.
        if not value.tzinfo:
            value = value.replace(tzinfo=timezone.utc)
        return value


app = application = App(__name__)
CORS(app)
app.url_map.converters['datetime'] = DateTimeConverter
