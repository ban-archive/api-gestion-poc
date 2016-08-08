from datetime import timedelta
from random import Random

import factory
from factory.fuzzy import FuzzyAttribute, FuzzyInteger, FuzzyText
from factory_peewee import PeeweeModelFactory

from ban.auth import models as auth_models
from ban.core import models
from ban.utils import utcnow


class BaseTestModel(PeeweeModelFactory):

    @classmethod
    def _setup_next_sequence(cls, *args, **kwargs):
        # Workaround https://github.com/cam-stitt/factory_boy-peewee/pull/6.
        return 1

    class Meta:
        database = models.db


class UserFactory(BaseTestModel):
    username = FuzzyText(length=12)
    # Avoid running bcrypt crypting at each test.
    # password = factory.PostGenerationMethodCall('set_password', 'password')
    email = factory.LazyAttribute(lambda obj: '%s@example.com' % obj.username)

    class Meta:
        model = auth_models.User


class ClientFactory(BaseTestModel):
    name = FuzzyText(length=54)
    user = factory.SubFactory(UserFactory)
    client_secret = FuzzyText(length=54)
    redirect_uris = ['http://localhost/authorize']
    grant_type = auth_models.Client.GRANT_CLIENT_CREDENTIALS
    flag_id = 'laposte'

    class Meta:
        model = auth_models.Client


class SessionFactory(BaseTestModel):
    user = factory.SubFactory(UserFactory)
    client = factory.SubFactory(ClientFactory)
    ip = '127.0.0.1'
    email = 'yeehoo@yay.com'

    class Meta:
        model = auth_models.Session


class TokenFactory(BaseTestModel):
    session = factory.SubFactory(SessionFactory)
    token_type = 'password'
    access_token = FuzzyText(length=50)
    refresh_token = FuzzyText(length=50)
    scope = 'contrib'
    expires = factory.LazyAttribute(
                            lambda x: utcnow() + timedelta(minutes=50))

    class Meta:
        model = auth_models.Token


class BaseFactory(BaseTestModel):
    created_by = factory.SubFactory(SessionFactory)
    modified_by = factory.SubFactory(SessionFactory)


class MunicipalityFactory(BaseFactory):
    name = "Montbrun-Bocage"
    insee = FuzzyAttribute(lambda: str(Random().randint(10000, 97000)))
    siren = FuzzyAttribute(lambda: str(Random().randint(100000000, 300000000)))

    class Meta:
        model = models.Municipality


class PostCodeFactory(BaseFactory):
    name = 'Test PostCode Area Name'
    code = FuzzyInteger(10000, 97000)
    municipality = factory.SubFactory(MunicipalityFactory)

    class Meta:
        model = models.PostCode


class GroupFactory(BaseFactory):
    name = "Rue des Pyrénées"
    kind = "way"
    municipality = factory.SubFactory(MunicipalityFactory)

    class Meta:
        model = models.Group


class HouseNumberFactory(BaseFactory):
    number = "18"
    ordinal = "bis"
    parent = factory.SubFactory(GroupFactory)

    @factory.post_generation
    def ancestors(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.ancestors.add(extracted)

    class Meta:
        model = models.HouseNumber


class PositionFactory(BaseFactory):
    center = (-1.1111, 48.8888)
    housenumber = factory.SubFactory(HouseNumberFactory)
    kind = models.Position.ENTRANCE
    positioning = models.Position.IMAGERY

    class Meta:
        model = models.Position
