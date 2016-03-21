import json

import falcon
from ban.core import models

from ..factories import HouseNumberFactory, MunicipalityFactory, GroupFactory
from .utils import authorize


def test_get_group(get, url):
    street = GroupFactory(name="Rue des Boulets")
    resp = get(url('group-resource', id=street.id, identifier="id"))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_group_without_explicit_identifier(get, url):
    street = GroupFactory(name="Rue des Boulets")
    resp = get(url('group-resource', identifier=street.id))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_group_with_fantoir(get, url):
    street = GroupFactory(name="Rue des Boulets")
    resp = get(url('group-resource', id=street.fantoir, identifier="fantoir"))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_group_with_pk(get, url):
    street = GroupFactory(name="Rue des Boulets")
    resp = get(url('group-resource', id=street.pk, identifier="pk"))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_group_housenumbers(get, url):
    street = GroupFactory()
    hn1 = HouseNumberFactory(number="1", parent=street)
    hn2 = HouseNumberFactory(number="2", parent=street)
    hn3 = HouseNumberFactory(number="3", parent=street)
    resp = get(url('group-housenumbers', identifier=street.id))
    assert resp.json['total'] == 3
    assert resp.json['collection'][0] == hn1.as_list
    assert resp.json['collection'][1] == hn2.as_list
    assert resp.json['collection'][2] == hn3.as_list


@authorize
def test_create_group(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": municipality.id,
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['name'] == 'Rue de la Plage'
    assert resp.json['municipality']['id'] == municipality.id
    assert models.Group.select().count() == 1
    uri = "https://falconframework.org{}".format(url('group-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_can_create_group_without_kind(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": municipality.id,
    }
    resp = client.post('/group', data)
    assert resp.status == falcon.HTTP_422


@authorize
def test_create_group_with_municipality_insee(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "insee:{}".format(municipality.insee),
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status == falcon.HTTP_201
    assert models.Group.select().count() == 1
    uri = "https://falconframework.org{}".format(url('group-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_create_group_with_municipality_siren(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "siren:{}".format(municipality.siren),
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status == falcon.HTTP_201
    assert models.Group.select().count() == 1


@authorize
def test_create_group_with_bad_municipality_siren(client):
    MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "siren:{}".format('bad'),
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status == falcon.HTTP_422
    assert not models.Group.select().count()


@authorize
def test_create_group_with_invalid_municipality_identifier(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "invalid:{}".format(municipality.insee),
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status == falcon.HTTP_422
    assert not models.Group.select().count()


def test_get_group_versions(get, url):
    street = GroupFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    uri = url('group-versions', identifier=street.id)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert len(resp.json['collection']) == 2
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['name'] == 'Rue de la Paix'
    assert resp.json['collection'][1]['name'] == 'Rue de la Guerre'


def test_get_group_version(get, url):
    street = GroupFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    uri = url('group-version', identifier=street.id, version=1)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Rue de la Paix'
    assert resp.json['version'] == 1
    uri = url('group-version', identifier=street.id, version=2)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Rue de la Guerre'
    assert resp.json['version'] == 2


def test_get_group_unknown_version_should_go_in_404(get, url):
    street = GroupFactory(name="Rue de la Paix")
    uri = url('group-version', identifier=street.id, version=2)
    resp = get(uri)
    assert resp.status == falcon.HTTP_404


@authorize
def test_delete_street(client, url):
    street = GroupFactory()
    uri = url('group-resource', identifier=street.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_204
    assert not models.Group.select().count()


def test_cannot_delete_group_if_not_authorized(client, url):
    street = GroupFactory()
    uri = url('group-resource', identifier=street.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_401
    assert models.Group.get(models.Group.id == street.id)


@authorize
def test_cannot_delete_group_if_linked_to_housenumber(client, url):
    street = GroupFactory()
    HouseNumberFactory(parent=street)
    uri = url('group-resource', identifier=street.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_409
    assert models.Group.get(models.Group.id == street.id)


@authorize
def test_create_district_with_json_string_as_attribute(client, url):
    assert not models.Group.select().count()
    municipality = MunicipalityFactory()
    data = {
        "name": "Lhomme",
        "attributes": json.dumps({"key": "value"}),
        "municipality": municipality.id,
        "kind": models.Group.AREA,
    }
    resp = client.post(url('group'), data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['attributes'] == {"key": "value"}
