import falcon
from falcon_oauth.provider.oauth2 import OAuthProvider
from ban.auth import models

from ban.core import context
from ban.utils import is_uuid4
from .wsgi import app

auth = OAuthProvider()


@auth.clientgetter
def clientgetter(client_id):
    # FIXME Allow direct token access for dev with email/pwd
    if not is_uuid4(client_id):
        return False
    return models.Client.first(models.Client.client_id == client_id)


@auth.usergetter
def usergetter(username, password, client, req):
    user = models.User.first(models.User.username == username)
    if user and user.check_password(password):
        return user
    return None


@auth.tokengetter
def tokengetter(access_token=None, refresh_token=None):
    if access_token:
        token = models.Token.first(models.Token.access_token == access_token)
        if token:
            context.set('session', token.session)
            return token


@auth.tokensetter
def tokensetter(metadata, req, *args, **kwargs):
    # req: oauthlib.Request (not falcon one).
    metadata.update(dict(req.decoded_body))
    metadata['client'] = req.client_id
    token = models.Token.create_with_session(**metadata)
    if not token:
        raise falcon.HTTPBadRequest('Missing payload', 'Missing payload')


@auth.grantgetter
def grantgetter(client_id, code):
    if not is_uuid4(client_id):
        return False
    return models.Grant.first(models.Grant.client.client_id == client_id,
                              models.Grant.code == code)


class Token:

    @auth.token_endpoint
    def on_post(self, req, resp, *args, **kwargs):
        """Get a token to use the API."""
        return {}

app.register_resource(Token())
