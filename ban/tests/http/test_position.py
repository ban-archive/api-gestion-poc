import json

import falcon
from ban.core import models
from ban.core.encoder import dumps

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
def test_get_position_collection_can_be_filtered_by_bbox(get, url):
    position = PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2, south=0, west=0, east=2)
    resp = get(url('position', query_string=bbox))
    assert resp.json['total'] == 1
    # JSON transform internals tuples to lists.
    resource = position.as_resource
    assert resp.json['collection'][0] == json.loads(dumps(resource))


@authorize
def test_get_position_bbox_allows_floats(get, url):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2.23, south=0.12, west=0.56, east=2.34)
    resp = get(url('position', query_string=bbox))
    assert resp.json['total'] == 1


@authorize
def test_get_position_missing_bbox_param_makes_bbox_ignored(get, url):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2, south=0, west=0)
    resp = get(url('position', query_string=bbox))
    assert resp.json['total'] == 2


@authorize
def test_get_position_invalid_bbox_param_returns_bad_request(get, url):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2, south=0, west=0, east='invalid')
    resp = get(url('position', query_string=bbox))
    assert resp.status == falcon.HTTP_400


@authorize
def test_get_position_collection_filtered_by_bbox_is_paginated(get, url):
    PositionFactory.create_batch(9, center=(1, 1))
    params = dict(north=2, south=0, west=0, east=2, limit=5)
    PositionFactory(center=(-1, -1))
    resp = get(url('position', query_string=params))
    page1 = resp.json
    assert len(page1['collection']) == 5
    assert page1['total'] == 9
    assert 'next' in page1
    assert 'previous' not in page1
    resp = get(page1['next'])
    page2 = resp.json
    assert len(page2['collection']) == 4
    assert page2['total'] == 9
    assert 'next' not in page2
    assert 'previous' in page2
    resp = get(page2['previous'])
    assert resp.json == page1


@authorize
def test_get_position_collection_filtered_by_1_kind_param(get, url):
    PositionFactory(kind='entrance')
    PositionFactory(kind='exit')
    resp = get(url('position', query_string={'kind': 'entrance'}))
    assert resp.status == falcon.HTTP_200
    assert resp.json['total'] == 1


@authorize
def test_get_position_collection_filtered_by_2_equals_kind_params(get, url):
    PositionFactory(kind='entrance')
    PositionFactory(kind='exit')
    # 'kind' given by the user is used twice but with the same value.
    params = (('kind', 'entrance'), ('kind', 'entrance'))
    resp = get(url('position', query_string=params))
    assert resp.status == falcon.HTTP_200
    assert resp.json['total'] == 1


@authorize
def test_get_position_collection_filtered_by_2_diff_kind_params(get, url):
    PositionFactory(kind='entrance')
    PositionFactory(kind='exit')
    # 'kind' given by the user is used with 2 differents values.
    params = (('kind', 'entrance'), ('kind', 'exit'))
    resp = get(url('position', query_string=params))
    assert resp.status == falcon.HTTP_200
    assert resp.json['total'] == 2


@authorize
def test_get_position_collection_can_be_filtered_by_1_kind_and_1_pk(get, url):
    PositionFactory(kind='entrance')
    PositionFactory(kind='exit')
    # Only 'kind' param will be used to filter, not 'pk' one.
    params = (('kind', 'entrance'), ('pk', '405'))
    resp = get(url('position', query_string=params))
    assert resp.status == falcon.HTTP_200
    assert resp.json['total'] == 1
