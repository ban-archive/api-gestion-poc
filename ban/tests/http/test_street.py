import falcon
from ban.core import models

from ..factories import HouseNumberFactory, MunicipalityFactory, StreetFactory
from .utils import authorize


def test_get_street(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url('street-resource', id=street.id, identifier="id"))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_street_without_explicit_identifier(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url('street-resource', identifier=street.id))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_street_with_fantoir(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url('street-resource', id=street.fantoir, identifier="fantoir"))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_street_housenumbers(get, url):
    street = StreetFactory()
    hn1 = HouseNumberFactory(number="1", street=street)
    hn2 = HouseNumberFactory(number="2", street=street)
    hn3 = HouseNumberFactory(number="3", street=street)
    resp = get(url('street-housenumbers', identifier=street.id))
    assert resp.json['total'] == 3
    assert resp.json['collection'][0] == hn1.as_list
    assert resp.json['collection'][1] == hn2.as_list
    assert resp.json['collection'][2] == hn3.as_list


@authorize
def test_create_street(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": municipality.id,
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['name'] == 'Rue de la Plage'
    assert resp.json['municipality']['id'] == municipality.id
    assert models.Street.select().count() == 1
    uri = "https://falconframework.org{}".format(url('street-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_create_street_with_municipality_insee(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "insee:{}".format(municipality.insee),
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_201
    assert models.Street.select().count() == 1
    uri = "https://falconframework.org{}".format(url('street-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_create_street_with_municipality_siren(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "siren:{}".format(municipality.siren),
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_201
    assert models.Street.select().count() == 1


@authorize
def test_create_street_with_bad_municipality_siren(client):
    MunicipalityFactory(name="Cabour")
    assert not models.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "siren:{}".format('bad'),
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_422
    assert not models.Street.select().count()


@authorize
def test_create_street_with_invalid_municipality_identifier(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "invalid:{}".format(municipality.insee),
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_422
    assert not models.Street.select().count()


def test_get_street_versions(get, url):
    street = StreetFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    uri = url('street-versions', identifier=street.id)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert len(resp.json['collection']) == 2
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['name'] == 'Rue de la Paix'
    assert resp.json['collection'][1]['name'] == 'Rue de la Guerre'


def test_get_street_version(get, url):
    street = StreetFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    uri = url('street-version', identifier=street.id, version=1)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Rue de la Paix'
    assert resp.json['version'] == 1
    uri = url('street-version', identifier=street.id, version=2)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Rue de la Guerre'
    assert resp.json['version'] == 2


def test_get_street_unknown_version_should_go_in_404(get, url):
    street = StreetFactory(name="Rue de la Paix")
    uri = url('street-version', identifier=street.id, version=2)
    resp = get(uri)
    assert resp.status == falcon.HTTP_404


@authorize
def test_delete_street(client, url):
    street = StreetFactory()
    uri = url('street-resource', identifier=street.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_204
    assert not models.Street.select().count()


def test_cannot_delete_street_if_not_authorized(client, url):
    street = StreetFactory()
    uri = url('street-resource', identifier=street.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_401
    assert models.Street.get(models.Street.id == street.id)


@authorize
def test_cannot_delete_street_if_linked_to_housenumber(client, url):
    street = StreetFactory()
    HouseNumberFactory(street=street)
    uri = url('street-resource', identifier=street.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_409
    assert models.Street.get(models.Street.id == street.id)
