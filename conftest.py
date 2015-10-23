import pytest

from django.core.urlresolvers import reverse

from ban.core import context
from ban.core.tests.factories import UserFactory


@pytest.fixture()
def user():
    return UserFactory()


@pytest.fixture()
def staffuser():
    return UserFactory(is_staff=True)


@pytest.fixture()
def loggedclient(client, user):
    context.set_user(user)
    client.login(username=user.username, password='password')
    return client


@pytest.fixture()
def url():
    def _(name, **kwargs):
        return reverse(name, kwargs=kwargs)
    return _
