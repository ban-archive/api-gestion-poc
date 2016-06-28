from functools import wraps

from ..factories import TokenFactory


def authorize(func):

    @wraps(func)
    def inner(*args, **kwargs):
        token = TokenFactory()

        def attach(kwargs):
            kwargs['headers']['Authorization'] = 'Bearer {}'.format(token.access_token)  # noqa

        # Subtly plug in authenticated user.
        if 'client' in kwargs:
            kwargs['client'].before(attach)
        elif 'get' in kwargs:
            kwargs['get'].__self__.before(attach)
        return func(*args, **kwargs)
    return inner
