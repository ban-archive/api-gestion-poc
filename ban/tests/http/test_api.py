import json
from functools import wraps

import falcon
import pytest

from ban.http import resources as http

from ..factories import (HouseNumberFactory, MunicipalityFactory,
                         PositionFactory, StreetFactory, TokenFactory)

pytestmark = pytest.mark.django_db


def log_in(func):

    def attach(kwargs):
        token = TokenFactory()
        kwargs['headers']['Authorization'] = 'Bearer {}'.format(token.access_token)  # noqa

    @wraps(func)
    def inner(*args, **kwargs):
        # Subtly plug in authenticated user.
        if 'client' in kwargs:
            kwargs['client'].before(attach)
        return func(*args, **kwargs)
    return inner


@pytest.mark.xfail
@pytest.mark.parametrize('name,kwargs,expected', [
    ['api:position', {"ref": 1, "key": "id"}, '/api/position/id/1/'],
    ['api:position', {}, '/api/position/'],
    ['api:housenumber', {"ref": 1, "key": "id"}, '/api/housenumber/id/1/'],
    ['api:housenumber', {"ref": "93031_1491H_84_BIS", "key": "cia"}, '/api/housenumber/cia/93031_1491H_84_BIS/'],  # noqa
    ['api:housenumber', {}, '/api/housenumber/'],
    ['api:street', {"ref": 1, "key": "id"}, '/api/street/id/1/'],
    ['api:street', {"ref": "930310644M", "key": "fantoir"}, '/api/street/fantoir/930310644M/'],  # noqa
    ['api:street', {}, '/api/street/'],
    ['api:municipality', {"ref": 1, "key": "id"}, '/api/municipality/id/1/'],
    ['api:municipality', {"ref": "93031", "key": "insee"}, '/api/municipality/insee/93031/'],  # noqa
    ['api:municipality', {"ref": "93031321", "key": "siren"}, '/api/municipality/siren/93031321/'],  # noqa
    ['api:municipality', {}, '/api/municipality/'],
])
def test_api_url(name, kwargs, expected):
    assert reverse(name, kwargs=kwargs) == expected


def test_invalid_identifier_returns_400(get):
    resp = get('/position/invalid:22')
    assert resp.status == falcon.HTTP_400


def test_cors(get):
    street = StreetFactory(name="Rue des Boulets")
    resp = get('/street/id:' + str(street.id))
    assert resp.headers["Access-Control-Allow-Origin"] == "*"
    assert resp.headers["Access-Control-Allow-Headers"] == "X-Requested-With"


def test_get_housenumber(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url(http.Housenumber, id=housenumber.id, identifier="id"))
    assert resp.json['number'] == "22"
    assert resp.json['id'] == housenumber.id
    assert resp.json['cia'] == housenumber.cia
    assert resp.json['street']['name'] == housenumber.street.name


def test_get_housenumber_without_explicit_identifier(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url(http.Housenumber, id=housenumber.id))
    assert resp.json['number'] == "22"
    assert resp.json['id'] == housenumber.id
    assert resp.json['cia'] == housenumber.cia
    assert resp.json['street']['name'] == housenumber.street.name


def test_get_housenumber_with_unknown_id_is_404(get, url):
    resp = get(url(http.Housenumber, id=22, identifier="id"))
    assert resp.status == falcon.HTTP_404


def test_get_housenumber_with_cia(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url(http.Housenumber, id=housenumber.cia, identifier="cia"))
    assert resp.json['number'] == "22"


def test_get_street(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url(http.Street, id=street.id, identifier="id"))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_street_without_explicit_identifier(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url(http.Street, id=street.id))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_street_with_fantoir(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url(http.Street, id=street.fantoir, identifier="fantoir"))
    assert resp.json['name'] == "Rue des Boulets"


@log_in
def test_create_position(client):
    housenumber = HouseNumberFactory(number="22")
    url = '/position'
    data = {
        "version": 1,
        "center": "(3, 4)",
        "housenumber": housenumber.id,
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['center']['lon'] == 3
    assert resp.json['center']['lat'] == 4
    assert resp.json['housenumber']['id'] == housenumber.id


@log_in
def test_replace_position(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(http.Position, id=position.id, identifier="id")
    data = {
        "version": 2,
        "center": (3, 4),
        "housenumber": position.housenumber.id
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 2
    assert resp.json['center']['lon'] == 3
    assert resp.json['center']['lat'] == 4


@log_in
def test_replace_position_with_existing_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(http.Position, id=position.id, identifier="id")
    data = {
        "version": 1,
        "center": (3, 4),
        "housenumber": position.housenumber.id
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['lon'] == 1
    assert resp.json['center']['lat'] == 2


@log_in
def test_replace_position_with_non_incremental_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(http.Position, id=position.id, identifier="id")
    data = {
        "version": 18,
        "center": (3, 4),
        "housenumber": position.housenumber.id
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['lon'] == 1
    assert resp.json['center']['lat'] == 2


@log_in
def test_update_position(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(http.Position, id=position.id, identifier="id")
    data = {
        "version": 2,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.id
    }
    resp = client.post(uri, data=data)
    assert resp.status == falcon.HTTP_200
    assert resp.json['id'] == position.id
    assert resp.json['center']['lon'] == 3.4
    assert resp.json['center']['lat'] == 5.678


@log_in
def test_update_position_with_existing_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(http.Position, id=position.id, identifier="id")
    data = {
        "version": 1,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.id
    }
    resp = client.post(uri, data=data)
    assert resp.status == falcon.HTTP_409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['lon'] == 1
    assert resp.json['center']['lat'] == 2


@log_in
def test_update_position_with_non_incremental_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    uri = url(http.Position, id=position.id, identifier="id")
    data = {
        "version": 3,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.id
    }
    resp = client.post(uri, data)
    assert resp.status == falcon.HTTP_409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['lon'] == 1
    assert resp.json['center']['lat'] == 2


@log_in
def test_create_housenumber(client):
    street = StreetFactory(name="Rue de Bonbons")
    data = {
        "version": 1,
        "number": 20,
        "street": street.id,
    }
    resp = client.post('/housenumber', data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['number'] == '20'
    assert resp.json['ordinal'] == ''
    assert resp.json['street']['id'] == street.id


@log_in
def test_create_housenumber_does_not_use_version_field(client):
    street = StreetFactory(name="Rue de Bonbons")
    data = {
        "version": 3,
        "number": 20,
        "street": street.id,
    }
    resp = client.post('/housenumber', data=data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['version'] == 1


@log_in
def test_replace_housenumber(client, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    uri = url(http.Housenumber, id=housenumber.id, identifier="id")
    data = {
        "version": 2,
        "number": housenumber.number,
        "ordinal": 'bis',
        "street": housenumber.street.id,
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['version'] == 2
    assert resp.json['number'] == '22'
    assert resp.json['ordinal'] == 'bis'
    assert resp.json['street']['id'] == housenumber.street.id


@log_in
def test_replace_housenumber_with_missing_field_fails(client, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    uri = url(http.Housenumber, id=housenumber.id, identifier="id")
    data = {
        "version": 2,
        "ordinal": 'bis',
        "street": housenumber.street.id,
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == '422'
    assert 'errors' in resp.json


@log_in
def test_create_street(client):
    municipality = MunicipalityFactory(name="Cabour")
    data = {
        "version": 1,
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": municipality.id,
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['name'] == 'Rue de la Plage'
    assert resp.json['municipality']['id'] == municipality.id


def test_get_municipality(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    uri = url(http.Municipality, id=municipality.id, identifier="id")
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


def test_get_municipality_without_explicit_identifier(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    uri = url(http.Municipality, id=municipality.id)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


def test_get_municipality_streets_collection(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    street = StreetFactory(municipality=municipality, name="Rue de la Plage")
    uri = url(http.Municipality, id=municipality.id, identifier="id",
              route="streets")
    resp = get(uri, query_string='pouet=ah')
    assert resp.status == falcon.HTTP_200
    assert resp.json['collection'][0] == street.as_resource
    assert resp.json['total'] == 1


def test_get_municipality_streets_collection_is_paginated(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    StreetFactory.create_batch(30, municipality=municipality)
    uri = url(http.Municipality, id=municipality.id, identifier="id",
              route="streets")
    resp = get(uri)
    page1 = json.loads(resp.body)
    assert len(page1['collection']) == 20
    assert page1['total'] == 30
    assert 'next' in page1
    assert 'previous' not in page1
    resp = get(page1['next'])
    page2 = json.loads(resp.body)
    assert len(page2['collection']) == 10
    assert page2['total'] == 30
    assert 'next' not in page2
    assert 'previous' in page2
    resp = get(page2['previous'])
    assert json.loads(resp.body) == page1


def test_get_municipality_versions(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    uri = url(http.Municipality, id=municipality.id, identifier="id",
              route="versions")
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
    uri = url(http.Municipality, id=municipality.id, identifier="id",
              route="versions", route_id=1)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Cabour'
    assert resp.json['version'] == 1
    uri = url(http.Municipality, id=municipality.id, identifier="id",
              route="versions", route_id=2)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Cabour2'
    assert resp.json['version'] == 2


def test_get_street_versions(get, url):
    street = StreetFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    uri = url(http.Street, id=street.id, identifier="id",
              route="versions")
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
    uri = url(http.Street, id=street.id, identifier="id",
              route="versions", route_id=1)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Rue de la Paix'
    assert resp.json['version'] == 1
    uri = url(http.Street, id=street.id, identifier="id",
              route="versions", route_id=2)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Rue de la Guerre'
    assert resp.json['version'] == 2


def test_invalid_route_is_not_found(get, url):
    resp = get(url(http.Street, id=1, identifier="id", route="invalid"))
    assert resp.status == falcon.HTTP_404
    resp = get(url(http.Street, id=1, identifier="id", route="save_object"))
    assert resp.status == falcon.HTTP_404
