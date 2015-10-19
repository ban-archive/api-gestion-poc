import json

import pytest
from django.contrib.gis.geos import Point
from django.core.urlresolvers import reverse

from ban.core.tests.factories import (HouseNumberFactory, PositionFactory,
                                      StreetFactory, MunicipalityFactory)

pytestmark = pytest.mark.django_db


def test_position_url():
    assert reverse('api:position', kwargs={"ref": 1}) == '/api/position/1/'
    assert reverse('api:position') == '/api/position/'


def test_housenumber_url():
    assert reverse('api:housenumber',
                   kwargs={"ref": 1}) == '/api/housenumber/1/'
    assert reverse('api:housenumber') == '/api/housenumber/'


def test_street_url():
    assert reverse('api:street', kwargs={"ref": 1}) == '/api/street/1/'
    assert reverse('api:street') == '/api/street/'


def test_get_position(client):
    position = PositionFactory(source="XXX")
    resp = client.get(reverse('api:position', kwargs={'ref': position.pk}))
    content = json.loads(resp.content.decode())
    assert content['source'] == "XXX"


def test_get_housenumber(client):
    housenumber = HouseNumberFactory(number="22")
    resp = client.get(reverse('api:housenumber', kwargs={'ref': housenumber.pk}))
    content = json.loads(resp.content.decode())
    assert content['number'] == "22"
    assert content['id'] == housenumber.pk
    assert content['cia'] == housenumber.cia
    assert content['street']['name'] == housenumber.street.name


def test_get_housenumber_with_cia(client):
    housenumber = HouseNumberFactory(number="22")
    resp = client.get(reverse('api:housenumber', kwargs={'ref': housenumber.cia}))
    content = json.loads(resp.content.decode())
    assert content['number'] == "22"


def test_get_street(client):
    street = StreetFactory(name="Rue des Boulets")
    resp = client.get(reverse('api:street', kwargs={'ref': street.pk}))
    content = json.loads(resp.content.decode())
    assert content['name'] == "Rue des Boulets"


def test_get_street_with_fantoir(client):
    street = StreetFactory(name="Rue des Boulets")
    resp = client.get(reverse('api:street', kwargs={'ref': street.fantoir}))
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
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['center']['lon'] == 3
    assert content['center']['lat'] == 4
    assert content['housenumber']['id'] == housenumber.pk


def test_replace_position(loggedclient):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    url = reverse('api:position', kwargs={'ref': position.pk})
    data = {
        "version": 2,
        "center": (3, 4),
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.put(url, json.dumps(data))
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['version'] == 2
    assert content['center']['lon'] == 3
    assert content['center']['lat'] == 4


def test_replace_position_with_existing_version_fails(loggedclient):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    url = reverse('api:position', kwargs={'ref': position.pk})
    data = {
        "version": 1,
        "center": (3, 4),
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.put(url, json.dumps(data))
    assert resp.status_code == 409
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['version'] == 1
    assert content['center']['lon'] == 1
    assert content['center']['lat'] == 2


def test_replace_position_with_non_incremental_version_fails(loggedclient):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    url = reverse('api:position', kwargs={'ref': position.pk})
    data = {
        "version": 18,
        "center": (3, 4),
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.put(url, json.dumps(data))
    assert resp.status_code == 409
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['version'] == 1
    assert content['center']['lon'] == 1
    assert content['center']['lat'] == 2


def test_update_position(loggedclient):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    url = reverse('api:position', kwargs={'ref': position.pk})
    data = {
        "version": 2,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.post(url, data)
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['center']['lon'] == 3.4
    assert content['center']['lat'] == 5.678


def test_update_position_with_existing_version_fails(loggedclient):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    url = reverse('api:position', kwargs={'ref': position.pk})
    data = {
        "version": 1,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.post(url, data)
    assert resp.status_code == 409
    content = json.loads(resp.content.decode())
    assert content['id'] == position.pk
    assert content['version'] == 1
    assert content['center']['lon'] == 1
    assert content['center']['lat'] == 2


def test_update_position_with_non_incremental_version_fails(loggedclient):
    position = PositionFactory(source="XXX", center=Point(1, 2))
    url = reverse('api:position', kwargs={'ref': position.pk})
    data = {
        "version": 3,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.pk
    }
    resp = loggedclient.post(url, data)
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
    assert resp.status_code == 200
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
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['version'] == 1


def test_replace_housenumber(loggedclient):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    url = reverse('api:housenumber', kwargs={'ref': housenumber.pk})
    data = {
        "version": 2,
        "number": housenumber.number,
        "ordinal": 'bis',
        "street": housenumber.street.pk,
    }
    resp = loggedclient.put(url, json.dumps(data))
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['version'] == 2
    assert content['number'] == '22'
    assert content['ordinal'] == 'bis'
    assert content['street']['id'] == housenumber.street.pk


def test_replace_housenumber_with_missing_field_fails(loggedclient):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    url = reverse('api:housenumber', kwargs={'ref': housenumber.pk})
    data = {
        "version": 2,
        "ordinal": 'bis',
        "street": housenumber.street.pk,
    }
    resp = loggedclient.put(url, json.dumps(data))
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
    assert resp.status_code == 200
    content = json.loads(resp.content.decode())
    assert content['id']
    assert content['name'] == 'Rue de la Plage'
    assert content['municipality']['id'] == municipality.pk
