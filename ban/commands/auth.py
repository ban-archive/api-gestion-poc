import sys

from ban.auth.models import Token, User
from ban.commands import command
from ban.core import context

from . import helpers


@command
@helpers.session
def dummytoken(**kwargs):
    """Create a dummy token for dev."""
    session = context.get('session')
    Token.delete().where(Token.access_token == 'token').execute()
    Token.create(session=session.id, access_token="token", expires_in=3600*24)
    sys.stdout.write('Created token "token"')


@command
def createuser(username=None, email=None, is_staff=False, **kwargs):
    """Create a user.

    is_staff    set user staff
    """
    if not username:
        username = helpers.prompt('Username')
    if not email:
        email = helpers.prompt('Email')
    password = helpers.prompt('Password', confirmation=True)
    validator = User.validator(username=username, email=email)
    if not validator.errors:
        user = validator.save()
        user.set_password(password)
        if is_staff:
            user.is_staff = True
            user.save()
    else:
        for field, error in validator.errors.items():
            sys.stderr.write('{}: {}\n'.format(field, error))
