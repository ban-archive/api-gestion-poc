from flask import Flask, make_response
from ban.core.encoder import dumps
from functools import wraps


class App(Flask):
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
        instance = cls()
        for name in dir(cls):
            func = getattr(instance, name)
            if hasattr(func, '_endpoints'):
                for endpoint in func._endpoints:
                    path, kwargs = endpoint
                    path = '{}{}'.format(cls.endpoint, path)
                    endpoint = ('{}-{}'.format(cls.__name__, func.__name__)
                                       .lower().replace('_', '-'))
                    self.add_url_rule(path, view_func=func, endpoint=endpoint,
                                      **kwargs)
        return cls


app = application = App(__name__)
