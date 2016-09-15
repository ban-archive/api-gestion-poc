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
        if 'test_client' in kwargs:
            client = kwargs['test_client']
        elif 'get' in kwargs:
            client = kwargs['get'].__self__
        elif 'delete' in kwargs:
            client = kwargs['delete'].__self__
        if client:
            client.content_type = 'application/json'
            # client.before(attach)
            client.headers.update({
                'Authorization': 'Bearer {}'.format(token.access_token)
            })
        return func(*args, **kwargs)
    return inner
