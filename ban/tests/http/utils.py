from functools import wraps

from ..factories import TokenFactory


def authorize(func):

    @wraps(func)
    def inner(*args, **kwargs):
        token_kwargs = {}
        if 'session' in kwargs:
            token_kwargs['session'] = kwargs['session']
        token = TokenFactory(**token_kwargs)

        def attach(kwargs):
            kwargs['headers']['Authorization'] = 'Bearer {}'.format(token.access_token)  # noqa

        # Subtly plug in authenticated user.
        client = None
        if 'client' in kwargs:
            client = kwargs['client']
        elif 'get' in kwargs:
            client = kwargs['get'].__self__
        if client:
            client.content_type = 'application/json'
            # client.before(attach)
        return func(*args, **kwargs)
    return inner
