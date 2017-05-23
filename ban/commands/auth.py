from ban.auth.models import Token, User, Client
from ban.commands import command, reporter
from ban.core import context

from . import helpers


@command
@helpers.session
def dummytoken(token, **kwargs):
    """Create a dummy token for dev."""
    session = context.get('session')
    Token.delete().where(Token.access_token == token).execute()
    Token.create(session=session.pk, access_token=token, expires_in=3600*24,
                 token_type='Bearer', scope='*')
    reporter.notice('Created token', token)


@command
def createuser(username=None, email=None, is_staff=False, **kwargs):
    """Create a user.

    is_staff    set user staff
    """
    if not username:
        username = helpers.prompt('Username')
    if not email:
        email = helpers.prompt('Email')
    password = helpers.prompt('Password', confirmation=True, hidden=True)
    validator = User.validator(username=username, email=email)
    if not validator.errors:
        user = validator.save()
        user.set_password(password)
        if is_staff:
            user.is_staff = True
            user.save()
        reporter.notice('Created', user)
    else:
        reporter.error('Errored', validator.errors)


@command
def listusers(**kwargs):
    """List registered users with details."""
    tpl = '{:<20} {}'
    print(tpl.format('username', 'email'))
    for user in User.select():
        print(tpl.format(user.username, user.email))


@command
def createclient(name=None, user=None, scopes=[], **kwargs):
    """Create a client.

    name    name of the client to create
    user    username or email of an existing user
    """
    if not name:
        name = helpers.prompt('Client name')
    if not user:
        user = helpers.prompt('User username or email')
    user_inst = User.first((User.username == user) | (User.email == user))
    if not user_inst:
        return reporter.error('User not found', user)
    if not scopes:
        scopes = helpers.prompt('Scopes (separated by spaces)').split()
        if not scopes:
            scopes = 'view'
    validator = Client.validator(name=name, user=user_inst, scopes=scopes)
    if validator.errors:
        return reporter.error('Errored', validator.errors)
    client = validator.save()
    reporter.notice('Created', client)
    listclients()


@command
def listclients(**kwargs):
    """List existing clients with details."""
    tpl = '{:<40} {:<40} {:<60} {}'
    print(tpl.format('name', 'client_id', 'client_secret', 'scopes'))
    for client in Client.select():
        print(tpl.format(client.name, str(client.client_id),
                         client.client_secret, ' '.join(client.scopes or [])))
