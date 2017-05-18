from ban.tests import factories
from ban.auth import models as amodels
from ban.core import models
from ban.commands.auth import (createclient)

from .http.utils import authorize


def test_create_client_with_scopes(monkeypatch):
    monkeypatch.setattr('ban.commands.helpers.prompt',
                        lambda *x, **wk: 'municipality_write group_write')
    user = factories.UserFactory()
    createclient(name='test client', user=user.username)
    client = amodels.Client.first()
    assert client.scopes == ['municipality_write', 'group_write']


def test_create_client_without_scopes(monkeypatch):
    monkeypatch.setattr('ban.commands.helpers.prompt', lambda *x, **wk: ' ')
    user = factories.UserFactory()
    createclient(name='test client', user=user.username)
    client = amodels.Client.first()
    assert client.scopes == ['view']


def test_create_token_with_scopes(client, monkeypatch):
    monkeypatch.setattr('ban.commands.helpers.prompt',
                        lambda *x, **wk: 'municipality_write')
    user = factories.UserFactory()
    createclient(name='test client', user=user.username)
    c = amodels.Client.first()
    resp = client.post('/token/', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
    })
    assert resp.status_code == 200
    token = amodels.Token.first()
    assert token.scopes == ['municipality_write']


def test_create_token_without_scopes(client, monkeypatch):
    monkeypatch.setattr('ban.commands.helpers.prompt', lambda *x, **wk: ' ')
    user = factories.UserFactory()
    createclient(name='test client', user=user.username)
    c = amodels.Client.first()
    resp = client.post('/token/', data={
        'grant_type': 'client_credentials',
        'client_id': str(c.client_id),
        'client_secret': c.client_secret,
        'ip': '1.2.3.4',
    })
    assert resp.status_code == 200
    token = amodels.Token.first()
    assert token.scopes == ['view']


@authorize('view')
def test_get_municipality_without_scopes(get):
    municipality = factories.MunicipalityFactory(name="Cabour")
    resp = get('/municipality/{}'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


@authorize('view')
def test_post_municipality_without_scopes(post):
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
    }
    resp = post('/municipality', data)
    assert resp.status_code == 401


@authorize('municipality_write')
def test_post_municipality_with_scopes(post):
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
    }
    resp = post('/municipality', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['name'] == 'Fornex'
    assert models.Municipality.select().count() == 1
