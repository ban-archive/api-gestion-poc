
from ban.core.versioning import IdentifierRedirect
from .utils import authorize


def test_cannot_create_redirect_if_not_authorized(client):
    resp = client.put('/redirect/municipality/insee:12345/insee:54321')
    assert resp.status_code == 401
    assert not IdentifierRedirect.select().count()


@authorize
def test_can_create_redirect(client):
    resp = client.put('/redirect/municipality/insee:12345/insee:54321')
    assert resp.status_code == 201
    assert IdentifierRedirect.select().count()
    redirect = IdentifierRedirect.first()
    assert redirect.from_identifier == 'insee'
    assert redirect.from_value == '12345'
    assert redirect.to_identifier == 'insee'
    assert redirect.to_value == '54321'


@authorize
def test_can_delete_redirect(client):
    IdentifierRedirect.create(from_identifier='insee', from_value='12345',
                              to_identifier='insee', to_value='54321',
                              model_name='Municipality')
    assert IdentifierRedirect.select().count()
    resp = client.delete('/redirect/municipality/insee:12345/insee:54321')
    assert resp.status_code == 204
    assert not IdentifierRedirect.select().count()


@authorize
def test_can_list_redirects_by_source(client):
    IdentifierRedirect.create(from_identifier='insee', from_value='12345',
                              to_identifier='insee', to_value='54321',
                              model_name='Municipality')
    assert IdentifierRedirect.select().count()
    resp = client.get('/redirect/municipality/?from=insee:12345')
    assert resp.status_code == 200
    assert resp.json['collection'] == [{
        'from': 'insee:12345',
        'to': 'insee:54321',
    }]


@authorize
def test_can_list_redirects_by_destination(client):
    IdentifierRedirect.create(from_identifier='insee', from_value='12345',
                              to_identifier='insee', to_value='54321',
                              model_name='Municipality')
    assert IdentifierRedirect.select().count()
    resp = client.get('/redirect/municipality/?to=insee:54321')
    assert resp.status_code == 200
    assert resp.json['collection'] == [{
        'from': 'insee:12345',
        'to': 'insee:54321',
    }]
