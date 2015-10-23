import json

import pytest
from django.contrib.gis.geos import Point
from django.core.urlresolvers import reverse

from ban.core.tests.factories import (HouseNumberFactory, PositionFactory,
                                      StreetFactory, MunicipalityFactory)

pytestmark = pytest.mark.django_db


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


def test_invalid_identifier_returns_400(client, url):
    resp = client.get(url('api:position', ref="value", key="invalid"))
    assert resp.status_code == 400


def test_get_housenumber(client, url):
    housenumber = HouseNumberFactory(number="22")
    resp = client.get(url('api:housenumber', ref=housenumber.pk, key="id"))
    content = json.loads(resp.content.decode())
    assert content['number'] == "22"
    assert content['id'] == housenumber.pk
    assert content['cia'] == housenumber.cia
    assert content['street']['name'] == housenumber.street.name


def test_get_housenumber_with_cia(client, url):
    housenumber = HouseNumberFactory(number="22")
    resp = client.get(url('api:housenumber', ref=housenumber.cia, key="cia"))
    content = json.loads(resp.content.decode())
    assert content['number'] == "22"


def test_get_street(client, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = client.get(url('api:street', ref=street.pk, key="id"))
    content = json.loads(resp.content.decode())
    assert content['name'] == "Rue des Boulets"


def test_get_street_with_fantoir(client, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = client.get(url('api:street', ref=street.fantoir, key="fantoir"))
    content = json.loads(resp.content.decode())
    assert content['name'] == "Rue des Boulets"


def test_create_position(loggedclient):
    housenumber = HouseNumberFactory(number="22")
    url = reverse('api:position')
    data = {
        "version": 1,
        "center": "(3, 4)",
        "housenumber": housenumber.pk,
    }
    resp = loggedclient.post(url, data)
    assert resp.status_code == 201
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['center']['lon'] == 3
    assert content['center']['lat'] == 4
    assert content['housenumber']['id'] == housenumber.pk


def test_replace_position(loggedclient, url):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    uri = url('api:position', ref=position.pk, key="id")
    data = {
        "version": 2,
        "center": (3, 4),
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.put(uri, json.dumps(data))
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['version'] == 2
    assert content['center']['lon'] == 3
    assert content['center']['lat'] == 4


def test_replace_position_with_existing_version_fails(loggedclient, url):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    uri = url('api:position', ref=position.pk, key="id")
    data = {
        "version": 1,
        "center": (3, 4),
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.put(uri, json.dumps(data))
    assert resp.status_code == 409
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['version'] == 1
    assert content['center']['lon'] == 1
    assert content['center']['lat'] == 2


def test_replace_position_with_non_incremental_version_fails(loggedclient,
                                                             url):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    uri = url('api:position', ref=position.pk, key="id")
    data = {
        "version": 18,
        "center": (3, 4),
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.put(uri, json.dumps(data))
    assert resp.status_code == 409
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['version'] == 1
    assert content['center']['lon'] == 1
    assert content['center']['lat'] == 2


def test_update_position(loggedclient, url):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    uri = url('api:position', ref=position.pk, key="id")
    data = {
        "version": 2,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.post(uri, data)
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['center']['lon'] == 3.4
    assert content['center']['lat'] == 5.678


def test_update_position_with_existing_version_fails(loggedclient, url):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    uri = url('api:position', ref=position.pk, key="id")
    data = {
        "version": 1,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.post(uri, data)
    assert resp.status_code == 409
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['version'] == 1
    assert content['center']['lon'] == 1
    assert content['center']['lat'] == 2


def test_update_position_with_non_incremental_version_fails(loggedclient, url):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    uri = url('api:position', ref=position.pk, key="id")
    data = {
        "version": 3,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.post(uri, data)
    assert resp.status_code == 409
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['version'] == 1
    assert content['center']['lon'] == 1
    assert content['center']['lat'] == 2


def test_create_housenumber(loggedclient):
    street = StreetFactory(name="Rue de Bonbons")
    url = reverse('api:housenumber')
    data = {
        "version": 1,
        "number": 20,
        "street": street.pk,
    }
    resp = loggedclient.post(url, data)
    assert resp.status_code == 201
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['number'] == '20'
    assert content['ordinal'] == ''
    assert content['street']['id'] == street.pk


def test_create_housenumber_does_not_use_version_field(loggedclient):
    street = StreetFactory(name="Rue de Bonbons")
    url = reverse('api:housenumber')
    data = {
        "version": 3,
        "number": 20,
        "street": street.pk,
    }
    resp = loggedclient.post(url, data)
    assert resp.status_code == 201
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['version'] == 1


def test_replace_housenumber(loggedclient, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    uri = url('api:housenumber', ref=housenumber.pk, key="id")
    data = {
        "version": 2,
        "number": housenumber.number,
        "ordinal": 'bis',
        "street": housenumber.street.pk,
    }
    resp = loggedclient.put(uri, json.dumps(data))
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['version'] == 2
    assert content['number'] == '22'
    assert content['ordinal'] == 'bis'
    assert content['street']['id'] == housenumber.street.pk


def test_replace_housenumber_with_missing_field_fails(loggedclient, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    uri = url('api:housenumber', ref=housenumber.pk, key="id")
    data = {
        "version": 2,
        "ordinal": 'bis',
        "street": housenumber.street.pk,
    }
    resp = loggedclient.put(uri, json.dumps(data))
    assert resp.status_code == 422
    content = json.loads(resp.content.decode())
    assert 'errors' in content


def test_create_street(loggedclient):
    municipality = MunicipalityFactory(name="Cabour")
    url = reverse('api:street')
    data = {
        "version": 1,
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": municipality.pk,
    }
    resp = loggedclient.post(url, data)
    assert resp.status_code == 201
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['name'] == 'Rue de la Plage'
    assert content['municipality']['id'] == municipality.pk


def test_get_municipality(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    uri = url('api:municipality', ref=municipality.pk, key="id")
    resp = client.get(uri)
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['name'] == 'Cabour'


def test_get_municipality_streets_collection(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    street = StreetFactory(municipality=municipality, name="Rue de la Plage")
    uri = url('api:municipality', ref=municipality.pk, key="id",
              path="streets")
    resp = client.get(uri)
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['collection'][0] == street.as_json
    assert content['total'] == 1


def test_get_municipality_streets_collection_is_paginated(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    StreetFactory.create_batch(30, municipality=municipality)
    uri = url('api:municipality', ref=municipality.pk, key="id",
              path="streets")
    resp = client.get(uri)
    page1 = json.loads(resp.content.decode())
    assert len(page1['collection']) == 20
    assert page1['total'] == 30
    assert 'next' in page1
    assert 'previous' not in page1
    resp = client.get(page1['next'])
    page2 = json.loads(resp.content.decode())
    assert len(page2['collection']) == 10
    assert page2['total'] == 30
    assert 'next' not in page2
    assert 'previous' in page2
    resp = client.get(page2['previous'])
    assert json.loads(resp.content.decode()) == page1
