from .utils import abort
from flask_oauthlib.provider import OAuth2Provider
from flask import request
from werkzeug.datastructures import ImmutableMultiDict

from ban.auth import models
from ban.core import context
from ban.utils import is_uuid4, utcnow
from datetime import timedelta

from .wsgi import app

auth = OAuth2Provider(app)


def json_to_form(func):
    def wrapper(*args, **kwargs):
        if not request.form:
            request.form = ImmutableMultiDict(request.json)
        return func(*args, **kwargs)
    return wrapper


@auth.clientgetter
def clientgetter(client_id):
    # FIXME Allow direct token access for dev with email/pwd
    if not is_uuid4(client_id):
        return False
    return models.Client.first(models.Client.client_id == client_id)


@auth.usergetter
def usergetter(username):
    user = models.User.first(models.User.username == username)
    if user:
        return user
    return None


@auth.tokengetter
def tokengetter(access_token=None):
    if access_token:
        token = models.Token.first(models.Token.access_token == access_token)
        if token:
            if token.expires > utcnow() and token.expires < utcnow()+ timedelta(minutes=30):
                token.expires = token.expires + timedelta(hours=1)
                token.save()
            context.set('session', token.session)
            # We use TZ aware datetime while Flask Oauthlib wants naive ones.
            token.expires = token.expires.replace(tzinfo=None)
            return token


@auth.tokensetter
def tokensetter(metadata, req):
    # req: oauthlib.Request (not Flask one).
    metadata.update(dict(req.decoded_body))
    metadata['client'] = req.client_id
    token, error = models.Token.create_with_session(**metadata)
    if not token:
        abort(400, error=error)


@auth.grantgetter
def grantgetter(client_id, code):
    if not is_uuid4(client_id):
        return False
    return models.Grant.first(models.Grant.client.client_id == client_id,
                              models.Grant.code == code)

#Necessaire pour OAuthLib
@auth.grantsetter
def grantsetter():
    pass


@app.route('/token', methods=['POST'])
@json_to_form
@auth.token_handler
def authorize(*args, **kwargs):
    """Get a token to use the API."""
    return None
