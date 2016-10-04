import pytest

from ban.auth import models
from ban.tests.factories import UserFactory, ClientFactory


def test_session_can_be_created_with_a_user():
    user = UserFactory()
    session = models.Session.create(user=user)
    assert session.user == user
    assert session.as_relation == {
        'id': session.pk,
        'user': user.username,
        'client': None
    }


def test_session_can_be_created_with_a_client():
    client = ClientFactory()
    session = models.Session.create(client=client)
    assert session.client == client
    assert session.as_relation == {
        'id': session.pk,
        'user': None,
        'client': client.name
    }


def test_session_should_have_either_a_client_or_a_user():
    with pytest.raises(ValueError):
        models.Session.create()


def test_session_can_be_created_with_a_client_and_an_valid_IPAddress():
    client = ClientFactory()
    session = models.Session.create(client=client, ip='192.168.0.1')
    assert session.ip == '192.168.0.1'


def test_session_can_not_be_created_with_a_client_and_an_invalid_IPAddress():
    client = ClientFactory()
    with pytest.raises(ValueError):
        models.Session.create(client=client, ip='999.999.999.999')


def test_session_can_be_created_with_a_user_and_an_valid_IPAddress():
    user = UserFactory()
    session = models.Session.create(user=user, ip='192.168.0.1')
    assert session.ip == '192.168.0.1'


def test_session_can_not_be_created_with_a_user_and_an_invalid_IPAddress():
    user = UserFactory()
    with pytest.raises(ValueError):
        models.Session.create(user=user, ip='999.999.999.999')
