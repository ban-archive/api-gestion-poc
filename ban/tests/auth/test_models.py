import pytest

from ban.auth import models
from ban.tests.factories import UserFactory, ClientFactory


def test_user_password_is_hashed():
    password = '!22@%lkjsdfé&'
    user = UserFactory()
    user.set_password(password)
    # Reload from db.
    user = models.User.get(models.User.id == user.id)
    assert user.password != password
    assert user.check_password(password)


def test_session_can_be_created_with_a_user():
    user = UserFactory()
    session = models.Session.create(user=user, status='admin')
    assert session.user == user
    assert session.serialize() == {
        'id': session.pk,
        'user': user.username,
        'client': None,
        'status': 'admin'
    }


def test_session_can_be_created_with_a_client():
    client = ClientFactory()
    session = models.Session.create(client=client, status='admin')
    assert session.client == client
    assert session.serialize() == {
        'id': session.pk,
        'user': None,
        'client': client.name,
        'status': 'admin'
    }


def test_session_should_have_either_a_client_or_a_user():
    with pytest.raises(ValueError):
        models.Session.create()
