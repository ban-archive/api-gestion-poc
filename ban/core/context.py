import threading

_thread_locals = threading.local()


def set(key, value):
    setattr(_thread_locals, key, value)


def get(key):
    getattr(_thread_locals, key, None)


def set_user(user):
    set('user', user)


def get_user():
    return get('user')


class ContextMiddleware(object):

    def process_request(self, request):
        _thread_locals.request = request

    def process_response(self, request, response):
        _thread_locals.request = None  # Try to make god happy
        return response
