import threading

_thread_locals = threading.local()


def set_user(user):
    _thread_locals.user = user


def get_user():
    return getattr(_thread_locals, 'user', None)


class ContextMiddleware(object):

    def process_request(self, request):
        _thread_locals.request = request

    def process_response(self, request, response):
        _thread_locals.request = None  # Try to make god happy
        return response
