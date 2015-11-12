import threading

_thread_locals = threading.local()


def set(key, value):
    setattr(_thread_locals, key, value)


def get(key):
    return getattr(_thread_locals, key, None)
