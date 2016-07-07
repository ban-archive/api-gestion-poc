import json

import falcon
from ban.core import models

from ..factories import HouseNumberFactory, PositionFactory
from .utils import authorize


@authorize
def test_create_position(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "kind": models.Position.ENTRANCE,
        "positioning": models.Position.IMAGERY,
        "housenumber": housenumber.id,
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_201
    position = models.Position.first()
    assert resp.json['id'] == position.id
    assert resp.json['center']['coordinates'] == [3, 4]
    assert resp.json['housenumber']['id'] == housenumber.id


@authorize
def test_create_position_with_name(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "kind": models.Position.BUILDING,
        "positioning": models.Position.IMAGERY,
        "housenumber": housenumber.id,
        "name": "bâtiment A"
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['name'] == "bâtiment A"


@authorize
def test_create_position_with_name_but_not_center(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "kind": models.Position.BUILDING,
        "positioning": models.Position.IMAGERY,
        "housenumber": housenumber.id,
        "name": "bâtiment A"
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_201


@authorize
def test_cannot_create_position_without_kind(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "positioning": models.Position.IMAGERY,
        "housenumber": housenumber.id,
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_422


@authorize
def test_cannot_create_position_without_invalid_kind(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "kind": "ENTRANCE",
        "positioning": models.Position.IMAGERY,
        "housenumber": housenumber.id,
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_422


@authorize
def test_cannot_create_position_without_center_and_name(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "kind": models.Position.ENTRANCE,
        "positioning": models.Position.IMAGERY,
        "housenumber": housenumber.id,
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_422
    assert 'center' in resp.json['errors']
    assert 'name' in resp.json['errors']


@authorize
def test_cannot_create_position_without_positioning(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "housenumber": housenumber.id,
        "kind": models.Position.ENTRANCE,
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_422


@authorize
def test_cannot_create_position_with_invalid_positioning(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "housenumber": housenumber.id,
        "kind": models.Position.ENTRANCE,
        "positioning": "GPS",
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_422


@authorize
def test_create_position_with_housenumber_cia(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "kind": models.Position.ENTRANCE,
        "positioning": models.Position.IMAGERY,
        "housenumber": 'cia:{}'.format(housenumber.cia),
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_201
    assert models.Position.select().count() == 1


@authorize
def test_create_position_with_bad_housenumber_cia_is_422(client):
    HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "kind": models.Position.ENTRANCE,
        "positioning": models.Position.IMAGERY,
        "housenumber": 'cia:{}'.format('xxx'),
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_422


@authorize
def test_replace_position(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 2,
        "center": (3, 4),
        "kind": models.Position.ENTRANCE,
        "positioning": models.Position.IMAGERY,
        "housenumber": position.housenumber.id
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 2
    assert resp.json['center']['coordinates'] == [3, 4]
    assert models.Position.select().count() == 1


@authorize
def test_replace_position_with_housenumber_cia(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 2,
        "center": (3, 4),
        "kind": models.Position.ENTRANCE,
        "positioning": models.Position.IMAGERY,
        "housenumber": 'cia:{}'.format(position.housenumber.cia)
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_200
    assert models.Position.select().count() == 1


@authorize
def test_replace_position_with_existing_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 1,
        "center": (3, 4),
        "kind": models.Position.ENTRANCE,
        "positioning": models.Position.IMAGERY,
        "housenumber": position.housenumber.id
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['coordinates'] == [1, 2]
    assert models.Position.select().count() == 1


@authorize
def test_replace_position_with_non_incremental_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 18,
        "center": (3, 4),
        "kind": models.Position.ENTRANCE,
        "positioning": models.Position.IMAGERY,
        "housenumber": position.housenumber.id
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['coordinates'] == [1, 2]
    assert models.Position.select().count() == 1


@authorize
def test_update_position(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 2,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.id
    }
    resp = client.post(uri, data=data)
    assert resp.status == falcon.HTTP_200
    assert resp.json['id'] == position.id
    assert resp.json['center']['coordinates'] == [3.4, 5.678]
    assert models.Position.select().count() == 1


@authorize
def test_update_position_with_cia(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 2,
        "center": "(3.4, 5.678)",
        "housenumber": 'cia:{}'.format(position.housenumber.cia)
    }
    resp = client.post(uri, data=data)
    assert resp.status == falcon.HTTP_200
    assert models.Position.select().count() == 1


@authorize
def test_update_position_with_existing_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 1,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.id
    }
    resp = client.post(uri, data=data)
    assert resp.status == falcon.HTTP_409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['coordinates'] == [1, 2]
    assert models.Position.select().count() == 1


@authorize
def test_update_position_with_non_incremental_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 3,
        "center": "(3.4, 5.678)",
        "housenumber": position.housenumber.id
    }
    resp = client.post(uri, data)
    assert resp.status == falcon.HTTP_409
    assert resp.json['id'] == position.id
    assert resp.json['version'] == 1
    assert resp.json['center']['coordinates'] == [1, 2]
    assert models.Position.select().count() == 1


@authorize
def test_patch_position_should_allow_to_update_only_some_fields(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 2,
        "center": "(3.4, 5.678)",
    }
    resp = client.patch(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id'] == position.id
    assert resp.json['center']['coordinates'] == [3.4, 5.678]
    assert resp.json['housenumber']['id'] == position.housenumber.id
    assert models.Position.select().count() == 1


@authorize
def test_patch_without_version_should_fail(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "center": "(3.4, 5.678)",
    }
    resp = client.patch(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_422


@authorize
def test_patch_with_wrong_version_should_fail(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 1,
        "center": "(3.4, 5.678)",
    }
    resp = client.patch(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_409


@authorize
def test_cannot_remove_center_and_name(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert models.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 2,
        "center": "",
        "name": ""
    }
    resp = client.patch(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_422
    assert "center" in resp.json["errors"]
    assert "name" in resp.json["errors"]


@authorize
def test_delete_position(client, url):
    position = PositionFactory()
    uri = url('position-resource', identifier=position.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_204
    assert not models.Position.select().count()


def test_cannot_delete_position_if_not_authorized(client, url):
    position = PositionFactory()
    uri = url('position-resource', identifier=position.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_401
    assert models.Position.get(models.Position.id == position.id)


@authorize
def test_position_select_use_default_orderby(get, url):
    PositionFactory(name="pos1")
    PositionFactory(name="pos2")
    uri = url('position')
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['name'] == 'pos1'
    assert resp.json['collection'][1]['name'] == 'pos2'
