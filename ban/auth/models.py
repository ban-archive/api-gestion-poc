import uuid
from datetime import timedelta

from ban import db
from ban.core.resource import ResourceModel

from ban.utils import utcnow
from .utils import generate_secret

__all__ = ['User', 'Client', 'Grant', 'Token']


_ = lambda x: x


class User(ResourceModel):
    identifiers = ['email']
    resource_fields = ['username', 'email', 'company']

    username = db.CharField(max_length=100, index=True)
    email = db.CharField(max_length=100, unique=True)
    company = db.CharField(max_length=100, null=True)
    is_staff = db.BooleanField(default=False, index=True)

    class Meta:
        database = db.database

    def __str__(self):
        return self.username


class Client(ResourceModel):
    identifiers = ['client_id']
    resource_fields = ['name', 'user', 'scopes', 'contributor_types']

    GRANT_CLIENT_CREDENTIALS = 'client_credentials'
    GRANT_TYPES = (
        (GRANT_CLIENT_CREDENTIALS, _('Client credentials')),
    )
    TYPE_IGN = 'ign'
    TYPE_LAPOSTE = 'laposte'
    TYPE_DGFIP = 'dgfip'
    TYPE_ETALAB = 'etalab'
    TYPE_OSM = 'osm'
    TYPE_SDIS = 'sdis'
    TYPE_MUNICIPAL = 'municipal_administration'
    TYPE_ADMIN = 'admin'
    TYPE_DEV = 'develop'
    TYPE_INSEE = 'insee'
    TYPE_VIEWER = 'viewer'
    CONTRIBUTOR_TYPE = (
        TYPE_SDIS,
        TYPE_OSM,
        TYPE_LAPOSTE,
        TYPE_IGN,
        TYPE_DGFIP,
        TYPE_ETALAB,
        TYPE_MUNICIPAL,
        TYPE_ADMIN,
        TYPE_INSEE,
        TYPE_DEV,
        TYPE_VIEWER)

    client_id = db.UUIDField(unique=True, default=uuid.uuid4)
    name = db.CharField(max_length=100)
    user = db.ForeignKeyField(User)
    client_secret = db.CharField(unique=True, max_length=55)
    redirect_uris = db.ArrayField(db.CharField)
    grant_type = db.CharField(choices=GRANT_TYPES)
    is_confidential = db.BooleanField(default=False)
    contributor_types = db.ArrayField(db.CharField, default=[TYPE_VIEWER], null=True)
    scopes = db.ArrayField(db.CharField, default=[], null=True)

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0] if self.redirect_uris else None

    @property
    def allowed_grant_types(self):
        return [id for id, name in self.GRANT_TYPES]

    #Necessaire pour OAuth
    @property
    def default_scopes(self):
        return self.scopes

    def save(self, *args, **kwargs):
        if not self.client_secret:
            self.client_secret = generate_secret()
            self.redirect_uris = ['http://localhost/authorize']  # FIXME
            self.grant_type = self.GRANT_CLIENT_CREDENTIALS
        if not self.contributor_types:
            self.contributor_types = ['viewer']
        super().save(*args, **kwargs)


class Grant(db.Model):
    user = db.ForeignKeyField(User)
    client = db.ForeignKeyField(Client)
    code = db.CharField(max_length=255, index=True, null=False)
    redirect_uri = db.CharField()
    scope = db.CharField(null=True)
    expires = db.DateTimeField()

    @property
    def scopes(self):
        return self.scope.split() if self.scope else None


class Session(db.Model):
    """Stores the minimum data to trace the changes. We have two scenarios:
    - one registered user (a developer?) create its own token, and then gets
      a nominative session
    - a client sends us IP and/or email from a remote user we don't know of
    """

    __openapi__ = """
        properties:
            id:
                type: integer
                description: primary key of the session
            client:
                type: string
                description: client name
            user:
                type: string
                description: user name
        """

    user = db.CachedForeignKeyField(User, null=True)
    client = db.CachedForeignKeyField(Client, null=True)
    ip = db.CharField(null=True)  # TODO IPField
    email = db.CharField(null=True)  # TODO EmailField
    contributor_type = db.CharField(null=True)

    def serialize(self, *args):
        # Pretend to be a resource for created_by/modified_by values in
        # resources serialization.
        # Should we also expose the email/ip? CNIL question to be solved.
        return {
            'id': self.pk,
            'client': self.client.name if self.client else None,
            'user': self.user.username if self.user else None,
            'contributor_type': self.contributor_type if self.contributor_type else None
        }

    def save(self, **kwargs):
        if not self.user and not self.client:
            raise ValueError('Session must have either a client or a user')
        if not self.contributor_type:
            raise ValueError('Session must have a contributor type')
        super().save(**kwargs)


class Token(db.Model):
    session = db.ForeignKeyField(Session)
    token_type = db.CharField(max_length=40)
    access_token = db.CharField(max_length=255)
    refresh_token = db.CharField(max_length=255, null=True)
    scopes = db.ArrayField(db.CharField, default=[], null=True)
    expires = db.DateTimeField()
    contributor_type = db.CharField(choices=Client.CONTRIBUTOR_TYPE, null=True)

    def __init__(self, **kwargs):
        expires_in = kwargs.pop('expires_in', 60 * 60 )
        kwargs['expires'] = utcnow() + timedelta(seconds=expires_in)
        super().__init__(**kwargs)

    def is_valid(self, scopes=None):
        """
        Checks if the access token is valid.
        :param scopes: An iterable containing the scopes to check or None
        """
        return not self.is_expired() and self.allow_scopes(scopes)

    def is_expired(self):
        """
        Check token expiration with timezone awareness
        """
        return utcnow() >= self.expires

    def allow_scopes(self, scopes):
        """
        Check if the token allows the provided scopes
        :param scopes: An iterable containing the scopes to check
        """
        if not scopes:
            return True

        provided_scopes = set(self.scope.split())
        resource_scopes = set(scopes)

        return resource_scopes.issubset(provided_scopes)

    @property
    def user(self):
        return self.session.user

    @classmethod
    def create_with_session(cls, **data):
        if not data.get('ip') and not data.get('email'):
            return None, None
        if not data.get('client_id'):
            return None, 'Client id missing'
        client = Client.first(Client.client_id == data['client_id'])
        if len(client.contributor_types) == 0:
            return None, 'Client has none contributor types'
        contributor_type = client.contributor_types[0]
        if data.get('contributor_type'):
            if data.get('contributor_type') not in client.contributor_types:
                return None, 'wrong contributor type : must be in the list {}'.format(client.contributor_types)
        if len(client.contributor_types) > 1:
            if not data.get('contributor_type'):
                return None, 'Contributor type missing'
            contributor_type = data.get('contributor_type')

        session_data = {
            "email": data.get('email'),
            "ip": data.get('ip'),
            "contributor_type": contributor_type,
            "client": client
        }
        session = Session.create(**session_data)  # get or create?
        data['session'] = session.pk
        data['scopes'] = client.scopes
        data['contributor_type'] = session.contributor_type
        if session.contributor_type == Client.TYPE_VIEWER:
            data['scopes'] = None
        return Token.create(**data), None
