"""
Very simple custom cache.
functools.lru_cache does not make it, as it only works with hashable types,
while we need peewee.Expression to be memoized.
On the other hand, we want to select which SQL queries will be cached (i.e. not
a goal to cache every get on housenumbers or positions), so we cannot just
cache every SelectQuery.get neither every Model.get.
"""

STORE = {}
UNSET = ...


def key(func):
    def wrapper(keys, *args, **kwargs):
        if isinstance(keys, (list, tuple)):
            keys = '|'.join(map(str, keys))
        return func(keys, *args, **kwargs)
    return wrapper


@key
def get(key):
    return STORE.get(key, UNSET)


@key
def set(key, value):
    STORE[key] = value


@key
def cache(key, func, *args, **kwargs):
    cached = get(key)
    if cached == UNSET:
        cached = func(*args, **kwargs)
        set(key, cached)
    return cached


def clear():
    STORE.clear()
