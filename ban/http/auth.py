from flask_restplus import abort
from flask_oauthlib.provider import OAuth2Provider

from ban.auth import models
from ban.core import context
from ban.utils import is_uuid4

from .wsgi import app

auth = OAuth2Provider(app)


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
            # We use TZ aware datetime while Flask Oauthlib wants naive ones.
            token.expires = token.expires.replace(tzinfo=None)
            return token


@auth.tokensetter
def tokensetter(metadata, req, *args, **kwargs):
    # req: oauthlib.Request (not Flask one).
    metadata.update(dict(req.decoded_body))
    metadata['client'] = req.client_id
    token = models.Token.create_with_session(**metadata)
    if not token:
        abort(400, 'Missing payload')


@auth.grantgetter
def grantgetter(client_id, code):
    if not is_uuid4(client_id):
        return False
    return models.Grant.first(models.Grant.client.client_id == client_id,
                              models.Grant.code == code)


@auth.grantsetter
def grantsetter(client_id, code, request, *args, **kwargs):
    # Needed by flask-oauthlib, but not used by client_crendentials flow.
    pass


@app.route('/token/', methods=['POST'])
@auth.token_handler
def authorize(*args, **kwargs):
    """Get a token to use the API."""
    return None
