import falcon
import pytest

from ..factories import ClientFactory, UserFactory


def test_access_token_with_client_credentials_and_ip(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': c.client_id,
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
    })
    assert resp.status == falcon.HTTP_200
    assert 'access_token' in resp.json


def test_access_token_with_client_credentials_and_email(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': c.client_id,
        'client_secret': c.client_secret,
        'email': 'ba@to.fr',
    })
    assert resp.status == falcon.HTTP_200
    assert 'access_token' in resp.json


def test_access_token_with_client_credentials_missing_session_data(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': c.client_id,
        'client_secret': c.client_secret,
    })
    assert resp.status == falcon.HTTP_400


def test_access_token_with_client_credentials_wrong_client_id(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': '2ed004ef-54dc-4a66-92d6-6b64fd463353',
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
    })
    assert resp.status == falcon.HTTP_401


def test_access_token_with_client_credentials_invalid_uuid(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': 'invaliduuid',
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
    })
    assert resp.status == falcon.HTTP_401


@pytest.mark.xfail
def test_access_token_with_password(client):
    # TODO: We want a simple access for developers.
    user = UserFactory(password='password')
    resp = client.post('/token', data={
        'grant_type': 'password',
        'username': user.username,
        'password': 'password',
    })
    assert resp.status == falcon.HTTP_200
    assert 'access_token' in resp.json
