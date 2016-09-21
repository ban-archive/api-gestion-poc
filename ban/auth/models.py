import uuid
from datetime import datetime, timedelta

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
    # Allow null, because password is not a resource field, and thus cannot be
    # passed to validators.
    password = db.PasswordField(null=True)
    is_staff = db.BooleanField(default=False, index=True)

    class Meta:
        database = db.default

    def __str__(self):
        return self.username

    def set_password(self, password):
        self.password = password
        self.save()

    def check_password(self, password):
        return self.password.check_password(password)


class Client(ResourceModel):
    identifiers = ['client_id']
    resource_fields = ['name', 'user']

    GRANT_AUTHORIZATION_CODE = 'authorization_code'
    GRANT_IMPLICIT = 'implicit'
    GRANT_PASSWORD = 'password'
    GRANT_CLIENT_CREDENTIALS = 'client_credentials'
    GRANT_TYPES = (
        # (GRANT_AUTHORIZATION_CODE, _('Authorization code')),
        # (GRANT_IMPLICIT, _('Implicit')),
        (GRANT_PASSWORD, _('Resource owner password-based')),
        (GRANT_CLIENT_CREDENTIALS, _('Client credentials')),
    )
    default_scopes = ['contrib']
    FLAGS = ['ign', 'laposte', 'local_authority']
    FLAG_IDS = tuple((i, i) for i in FLAGS) + (None, 'None')

    client_id = db.UUIDField(unique=True, default=uuid.uuid4)
    name = db.CharField(max_length=100)
    user = db.ForeignKeyField(User)
    client_secret = db.CharField(unique=True, max_length=55)
    redirect_uris = db.ArrayField(db.CharField)
    grant_type = db.CharField(choices=GRANT_TYPES)
    is_confidential = db.BooleanField(default=False)
    flag_id = db.CharField(choices=FLAG_IDS, default=None, null=True)

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0] if self.redirect_uris else None

    @property
    def allowed_grant_types(self):
        return [id for id, name in self.GRANT_TYPES]

    def save(self, *args, **kwargs):
        if not self.client_secret:
            self.client_secret = generate_secret()
            self.redirect_uris = ['http://localhost/authorize']  # FIXME
            self.grant_type = self.GRANT_CLIENT_CREDENTIALS
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
    user = db.ForeignKeyField(User, null=True)
    client = db.ForeignKeyField(Client, null=True)
    ip = db.CharField(null=True)  # TODO IPField
    email = db.CharField(null=True)  # TODO EmailField

    @property
    def as_relation(self):
        # Pretend to be a resource for created_by/modified_by values in
        # resources serialization.
        # Should we also expose the email/ip? CNIL question to be solved.
        return {
            'id': self.pk,
            'client': self.client.name if self.client else None,
            'user': self.user.username if self.user else None
        }

    def serialize(self, *args):
        return {
            'id': self.pk,
            'client': self.client.name if self.client else None,
            'user': self.user.username if self.user else None
        }

    @property
    def id(self):
        # Pretend to be a resource for created_by/modified_by values in
        # list resources serialization.
        return self.pk

    def save(self, **kwargs):
        if not self.user and not self.client:
            raise ValueError('Session must have either a client or a user')
        super().save(**kwargs)


class Token(db.Model):
    session = db.ForeignKeyField(Session)
    token_type = db.CharField(max_length=40)
    access_token = db.CharField(max_length=255)
    refresh_token = db.CharField(max_length=255, null=True)
    scope = db.CharField(max_length=255)
    expires = db.DateTimeField()

    def __init__(self, **kwargs):
        expires_in = kwargs.pop('expires_in', 60 * 60)
        kwargs['expires'] = utcnow() + timedelta(seconds=expires_in)
        super().__init__(**kwargs)

    @property
    def scopes(self):
        # TODO: custom charfield
        return self.scope.split() if self.scope else None

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
            return None
        if not data.get('client_id'):
            return None
        session_data = {
            "email": data.get('email'),
            "ip": data.get('ip'),
            "client": Client.first(Client.client_id == data['client_id'])
        }
        session = Session.create(**session_data)  # get or create?
        data['session'] = session.pk
        return Token.create(**data)
