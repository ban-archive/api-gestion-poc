import pytest

from ban.auth import models
from ..factories import ClientFactory, UserFactory


def test_access_token_with_client_credentials_and_ip(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
        'contributor_type': 'develop'
    })
    assert resp.status_code == 200
    assert 'access_token' in resp.json


def test_access_token_with_client_credentials_and_email(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'email': 'ba@to.fr',
        'contributor_type': 'develop'
    })
    assert resp.status_code == 200
    assert 'access_token' in resp.json


def test_access_token_with_client_credentials_missing_session_data(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
    })
    assert resp.status_code == 400


def test_access_token_with_client_credentials_wrong_client_id(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': '2ed004ef-54dc-4a66-92d6-6b64fd463353',
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
    })
    assert resp.status_code == 401


def test_access_token_with_client_credentials_invalid_uuid(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': 'invaliduuid',
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
    })
    assert resp.status_code == 401


@pytest.mark.xfail
def test_access_token_with_password(client):
    # TODO: We want a simple access for developers.
    user = UserFactory(password='password')
    resp = client.post('/token', data={
        'grant_type': 'password',
        'username': user.username,
        'password': 'password',
    })
    assert resp.status_code == 200
    assert 'access_token' in resp.json


def test_can_request_token_with_json_enoded_body(client):
    c = ClientFactory()
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
        'contributor_type': 'develop'
    }, content_type='application/json')
    assert resp.status_code == 200
    assert 'access_token' in resp.json


def test_create_token_with_scopes(client):
    c = ClientFactory(scopes=['municipality_write'])
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4'
    })
    assert resp.status_code == 200
    token = models.Token.first()
    assert token.scopes == ['municipality_write']


def test_create_token_without_scopes(client):
    c = ClientFactory(scopes=[])
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
        'contributor_type': 'develop'
    })
    assert resp.status_code == 200
    token = models.Token.first()
    assert token.scopes == []


def test_cannot_create_token_without_contributor_type_none_in_client(client):
    c = ClientFactory(contributor_types=[])
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4'
    })
    assert resp.status_code == 400


def test_can_create_token_without_contributor_type_one_in_client(client):
    c = ClientFactory(contributor_types=["develop"])
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4'
    })
    assert resp.status_code == 200


def test_cannot_create_token_without_contributor_type_multiple_in_client(client):
    c = ClientFactory(contributor_types=["test", "viewer"])
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4'
    })
    assert resp.status_code == 400


def test_cannot_create_token_with_wrong_contributor_type(client):
    c = ClientFactory(contributor_types=["test", "viewer"])
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
        'contributor_type': 'wrong'
    })
    assert resp.status_code == 400


def test_token_viewer_should_not_have_scopes(client):
    c = ClientFactory(contributor_types=["viewer"], scopes=["municipality_write"])
    resp = client.post('/token', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4'
    })
    assert resp.status_code == 200
    token = models.Token.first()
    assert token.scopes == []
