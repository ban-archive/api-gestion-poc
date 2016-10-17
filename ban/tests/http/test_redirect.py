
from ban.core.versioning import Redirect
from .utils import authorize
from .. import factories


def test_cannot_create_redirect_if_not_authorized(client):
    factories.MunicipalityFactory(insee='54321')
    resp = client.put('/municipality/insee:54321/redirects/insee:12345')
    assert resp.status_code == 401
    assert not Redirect.select().count()


@authorize
def test_can_create_redirect_with_id(client):
    municipality = factories.MunicipalityFactory(insee='54321')
    resp = client.put('/municipality/{}/redirects/insee:12345'.format(
                      municipality.id))
    assert resp.status_code == 201
    assert Redirect.select().count()
    redirect = Redirect.first()
    assert redirect.identifier == 'insee'
    assert redirect.value == '12345'
    assert redirect.model_id == municipality.id


@authorize
def test_can_create_redirect_with_other_identifier(client):
    municipality = factories.MunicipalityFactory(insee='54321')
    resp = client.put('/municipality/insee:54321/redirects/insee:12345')
    assert resp.status_code == 201
    assert Redirect.select().count()
    redirect = Redirect.first()
    assert redirect.identifier == 'insee'
    assert redirect.value == '12345'
    assert redirect.model_id == municipality.id


@authorize
def test_can_delete_redirect(client):
    municipality = factories.MunicipalityFactory(insee='54321')
    Redirect.add(identifier='insee', value='12345', instance=municipality)
    assert Redirect.select().count()
    resp = client.delete('/municipality/{}/redirects/insee:12345'.format(
                         municipality.id))
    assert resp.status_code == 204
    assert not Redirect.select().count()


@authorize
def test_can_delete_redirect_with_other_identifier(client):
    municipality = factories.MunicipalityFactory(insee='54321')
    Redirect.add(identifier='insee', value='12345', instance=municipality)
    assert Redirect.select().count()
    resp = client.delete('/municipality/insee:54321/redirects/insee:12345')
    assert resp.status_code == 204
    assert not Redirect.select().count()


@authorize
def test_can_list_redirects(client):
    municipality = factories.MunicipalityFactory(insee='54321')
    Redirect.add(identifier='insee', value='12345', instance=municipality)
    resp = client.get('/municipality/insee:54321/redirects')
    assert resp.status_code == 200
    assert resp.json['collection'] == ['insee:12345']


@authorize
def test_invalid_identifier_should_raise_error(client):
    municipality = factories.MunicipalityFactory(insee='54321')
    resp = client.put('/municipality/{}/redirects/inse:12345'.format(
                      municipality.id))
    assert resp.status_code == 422
    assert resp.json['error'] == 'Invalid identifier: inse'
