from ban.auth.models import Token
from ban.commands import command
from ban.core import context
from .helpers import session


@command
@session
def dummytoken():
    """Create a dummy token for dev."""
    session = context.get('session')
    Token.delete().where(Token.access_token == 'token').execute()
    Token.create(session=session.id, access_token="token", expires_in=3600*24)
    print('Created token "token"')
