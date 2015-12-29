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
        "housenumber": housenumber.id,
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_201
    position = models.Position.first()
    assert resp.json['id'] == position.id
    assert resp.json['center']['coordinates'] == [3, 4]
    assert resp.json['housenumber']['id'] == housenumber.id


@authorize
def test_create_position_with_housenumber_cia(client):
    housenumber = HouseNumberFactory(number="22")
    assert not models.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
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
