import json

import falcon
from ban.core import models

from ..factories import MunicipalityFactory, PostCodeFactory, StreetFactory
from .utils import authorize


def test_get_municipality(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    uri = url('municipality-resource', identifier=municipality.id)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


def test_get_municipality_with_postcodes(get, url):
    postcode = PostCodeFactory(code="33000")
    municipality = MunicipalityFactory(name="Cabour")
    municipality.postcodes.add(postcode)
    uri = url('municipality-resource', identifier=municipality.id)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'
    assert resp.json['postcodes'] == ['33000']


def test_get_municipality_without_explicit_identifier(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    uri = url('municipality-resource', identifier=municipality.id)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


def test_get_municipality_streets_collection(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    street = StreetFactory(municipality=municipality, name="Rue de la Plage")
    uri = url('municipality-streets', identifier=municipality.id)
    resp = get(uri, query_string='pouet=ah')
    assert resp.status == falcon.HTTP_200
    assert resp.json['collection'][0] == street.as_list
    assert resp.json['total'] == 1


def test_get_municipality_streets_collection_is_paginated(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    StreetFactory.create_batch(6, municipality=municipality)
    uri = url('municipality-streets', identifier=municipality.id,
              query_string=dict(limit=4))
    resp = get(uri)
    page1 = resp.json
    assert len(page1['collection']) == 4
    assert page1['total'] == 6
    assert 'next' in page1
    assert 'previous' not in page1
    assert page1['next'] in resp.headers['Link']
    resp = get(page1['next'])
    page2 = resp.json
    assert len(page2['collection']) == 2
    assert page2['total'] == 6
    assert 'next' not in page2
    assert 'previous' in page2
    assert page2['previous'] in resp.headers['Link']
    resp = get(page2['previous'])
    assert resp.json == page1


def test_get_municipality_versions(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    uri = url('municipality-versions', identifier=municipality.id)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert len(resp.json['collection']) == 2
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['name'] == 'Cabour'
    assert resp.json['collection'][1]['name'] == 'Cabour2'


def test_get_municipality_version(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    uri = url('municipality-version', identifier=municipality.id, version=1)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Cabour'
    assert resp.json['version'] == 1
    uri = url('municipality-version', identifier=municipality.id, version=2)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Cabour2'
    assert resp.json['version'] == 2


def test_can_retrieve_municipality_with_old_insee(get, url):
    municipality = MunicipalityFactory(insee="12345")
    # This should create a redirect.
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    # Request with old insee.
    resp = get(url('municipality-resource', identifier='insee:12345'))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id'] == municipality.id
    assert resp.json['insee'] == '54321'


@authorize
def test_create_municipality(client, url):
    assert not models.Municipality.select().count()
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
    }
    resp = client.post(url('municipality'), data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['name'] == 'Fornex'
    assert models.Municipality.select().count() == 1
    uri = "https://falconframework.org{}".format(url('municipality-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_cannot_duplicate_municipality(client, url):
    MunicipalityFactory(insee="12345")
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
    }
    resp = client.post(url('municipality'), data)
    assert resp.status == falcon.HTTP_422
    assert resp.json['errors']['insee']
    assert '12345' in resp.json['errors']['insee']


@authorize
def test_create_municipality_with_postcodes(client, url):
    postcode = PostCodeFactory(code="09350")
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
        "postcodes": postcode.id
    }
    resp = client.post(url('municipality'), data)
    assert resp.status == falcon.HTTP_201
    municipality = models.Municipality.first()
    assert postcode in municipality.postcodes


@authorize
def test_patch_municipality_with_postcodes(client, url):
    postcode = PostCodeFactory(code="09350")
    municipality = MunicipalityFactory()
    data = {
        "version": 2,
        "postcodes": postcode.id
    }
    uri = url('municipality-resource', identifier=municipality.id)
    resp = client.post(uri, data)
    assert resp.status == falcon.HTTP_200
    municipality = models.Municipality.first()
    assert postcode in municipality.postcodes


@authorize
def test_create_municipality_with_one_alias(client, url):
    data = {
        "name": "Orvane",
        "insee": "12345",
        "siren": '123456789',
        "alias": 'Moret-sur-Loing'
    }
    resp = client.post(url('municipality'), data)
    assert resp.status == falcon.HTTP_201
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias


@authorize
def test_create_municipality_with_list_of_aliases(client, url):
    data = {
        "name": "Orvane",
        "insee": "12345",
        "siren": '123456789',
        "alias": ['Moret-sur-Loing', 'Another-Name']
    }
    headers = {'Content-Type': 'application/json'}
    resp = client.post(url('municipality'), json.dumps(data), headers=headers)
    assert resp.status == falcon.HTTP_201
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias
    assert 'Another-Name' in municipality.alias


@authorize
def test_patch_municipality_with_alias(client, url):
    municipality = MunicipalityFactory()
    data = {
        "version": 2,
        "alias": ['Moret-sur-Loing']
    }
    uri = url('municipality-resource', identifier=municipality.id)
    resp = client.patch(uri, json.dumps(data))
    assert resp.status == falcon.HTTP_200
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias


@authorize
def test_delete_municipality(client, url):
    municipality = MunicipalityFactory()
    uri = url('municipality-resource', identifier=municipality.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_204
    assert not models.Municipality.select().count()


def test_cannot_delete_municipality_if_not_authorized(client, url):
    municipality = MunicipalityFactory()
    uri = url('municipality-resource', identifier=municipality.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_401
    assert models.Municipality.get(models.Municipality.id == municipality.id)


@authorize
def test_cannot_delete_municipality_if_linked_to_street(client, url):
    municipality = MunicipalityFactory()
    StreetFactory(municipality=municipality)
    uri = url('municipality-resource', identifier=municipality.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_409
    assert models.Municipality.get(models.Municipality.id == municipality.id)


@authorize
def test_delete_unknown_municipality_should_return_not_found(client, url):
    uri = url('municipality-resource', identifier=11)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_404
