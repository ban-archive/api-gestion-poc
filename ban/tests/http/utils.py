from functools import wraps

from ..factories import TokenFactory


def authorize(func):

    @wraps(func)
    def inner(*args, **kwargs):
        token_kwargs = {}
        if 'session' in kwargs:
            token_kwargs['session'] = kwargs['session']
        token = TokenFactory(**token_kwargs)

        # Subtly plug in authenticated user.
        client = None
        if 'client' in kwargs:
            client = kwargs['client']
        for key in ['get', 'patch', 'post', 'put']:
            if key in kwargs:
                client = kwargs[key].__self__
        if client:
            client.content_type = 'application/json'
            client.extra_headers = {
                'Authorization': 'Bearer {}'.format(token.access_token)
            }
        return func(*args, **kwargs)
    return inner
