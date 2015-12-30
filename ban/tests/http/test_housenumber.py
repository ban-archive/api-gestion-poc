import json

import falcon
from ban.core import models

from ..factories import (DistrictFactory, HouseNumberFactory,
                         MunicipalityFactory, PositionFactory, PostCodeFactory,
                         StreetFactory)
from .utils import authorize


def test_get_housenumber(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.json['number'] == "22"
    assert resp.json['id'] == housenumber.id
    assert resp.json['cia'] == housenumber.cia
    assert resp.json['street']['name'] == housenumber.street.name


def test_get_housenumber_without_explicit_identifier(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.json['number'] == "22"
    assert resp.json['id'] == housenumber.id
    assert resp.json['cia'] == housenumber.cia
    assert resp.json['street']['name'] == housenumber.street.name


def test_get_housenumber_with_unknown_id_is_404(get, url):
    resp = get(url('housenumber-resource', identifier=22))
    assert resp.status == falcon.HTTP_404


def test_get_housenumber_with_cia(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url('housenumber-resource', id=housenumber.cia,
                   identifier="cia"))
    assert resp.json['number'] == "22"


def test_get_housenumber_with_districts(get, url):
    municipality = MunicipalityFactory()
    district = DistrictFactory(municipality=municipality)
    housenumber = HouseNumberFactory(districts=[district],
                                     municipality=municipality)
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.status == falcon.HTTP_200
    assert 'districts' in resp.json
    assert resp.json['districts'][0]['id'] == district.id
    assert resp.json['districts'][0]['name'] == district.name
    assert 'version' not in resp.json['districts'][0]


def test_get_housenumber_collection(get, url):
    objs = HouseNumberFactory.create_batch(5)
    resp = get(url('housenumber'))
    assert resp.json['total'] == 5
    for i, obj in enumerate(objs):
        assert resp.json['collection'][i] == obj.as_resource


def test_get_housenumber_collection_can_be_filtered_by_bbox(get, url):
    position = PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2, south=0, west=0, east=2)
    resp = get(url('housenumber', query_string=bbox))
    assert resp.json['total'] == 1
    # JSON transform internals tuples to lists.
    resource = position.housenumber.as_resource
    resource['center']['coordinates'] = list(resource['center']['coordinates'])  # noqa
    assert resp.json['collection'][0] == resource


def test_missing_bbox_param_makes_bbox_ignored(get, url):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2, south=0, west=0)
    resp = get(url('housenumber', query_string=bbox))
    assert resp.json['total'] == 2


def test_invalid_bbox_param_returns_bad_request(get, url):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2, south=0, west=0, east='invalid')
    resp = get(url('housenumber', query_string=bbox))
    assert resp.status == falcon.HTTP_400


def test_get_housenumber_collection_filtered_by_bbox_is_paginated(get, url):
    PositionFactory.create_batch(9, center=(1, 1))
    params = dict(north=2, south=0, west=0, east=2, limit=5)
    PositionFactory(center=(-1, -1))
    resp = get(url('housenumber', query_string=params))
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


def test_housenumber_with_two_positions_is_not_duplicated_in_bbox(get, url):
    position = PositionFactory(center=(1, 1))
    PositionFactory(center=(1.1, 1.1), housenumber=position.housenumber)
    bbox = dict(north=2, south=0, west=0, east=2)
    resp = get(url('housenumber', query_string=bbox))
    assert resp.json['total'] == 1
    # JSON transform internals tuples to lists.
    data = position.housenumber.as_resource
    data['center']['coordinates'] = list(data['center']['coordinates'])
    assert resp.json['collection'][0] == data


def test_get_housenumber_with_position(get, url):
    housenumber = HouseNumberFactory()
    PositionFactory(housenumber=housenumber, center=(1, 1))
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.json['center'] == {'coordinates': [1, 1], 'type': 'Point'}


def test_get_housenumber_with_postcode(get, url):
    postcode = PostCodeFactory(code="12345")
    housenumber = HouseNumberFactory(postcode=postcode)
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.json['postcode'] == "12345"


def test_get_housenumber_positions(get, url):
    housenumber = HouseNumberFactory()
    pos1 = PositionFactory(housenumber=housenumber, center=(1, 1))
    pos2 = PositionFactory(housenumber=housenumber, center=(2, 2))
    pos3 = PositionFactory(housenumber=housenumber, center=(3, 3))
    resp = get(url('housenumber-positions', identifier=housenumber.id))
    assert resp.json['total'] == 3

    def check(position):
        data = position.as_list
        # postgis uses tuples for coordinates, while json does not know
        # tuple and transforms everything to lists.
        data['center']['coordinates'] = list(data['center']['coordinates'])
        assert data in resp.json['collection']

    check(pos1)
    check(pos2)
    check(pos3)


@authorize
def test_create_housenumber(client):
    street = StreetFactory(name="Rue de Bonbons")
    assert not models.HouseNumber.select().count()
    data = {
        "number": 20,
        "street": street.id,
    }
    resp = client.post('/housenumber', data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['number'] == '20'
    assert resp.json['ordinal'] == ''
    assert resp.json['street']['id'] == street.id
    assert models.HouseNumber.select().count() == 1


@authorize
def test_create_housenumber_with_street_fantoir(client):
    street = StreetFactory(name="Rue de Bonbons")
    assert not models.HouseNumber.select().count()
    data = {
        "number": 20,
        "street": 'fantoir:{}'.format(street.fantoir),
    }
    resp = client.post('/housenumber', data)
    assert resp.status == falcon.HTTP_201
    assert models.HouseNumber.select().count() == 1


@authorize
def test_create_housenumber_does_not_honour_version_field(client):
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


@authorize
def test_create_housenumber_with_postcode_id(client):
    postcode = PostCodeFactory(code="12345")
    street = StreetFactory(name="Rue de Bonbons")
    data = {
        "number": 20,
        "street": 'fantoir:{}'.format(street.fantoir),
        "postcode": postcode.id
    }
    resp = client.post('/housenumber', data)
    assert resp.status == falcon.HTTP_201
    assert models.HouseNumber.select().count() == 1
    assert models.HouseNumber.first().postcode == postcode


@authorize
def test_create_housenumber_with_postcode_code(client):
    postcode = PostCodeFactory(code="12345")
    street = StreetFactory(name="Rue de Bonbons")
    data = {
        "number": 20,
        "street": 'fantoir:{}'.format(street.fantoir),
        "postcode": 'code:12345',
    }
    resp = client.post('/housenumber', data)
    assert resp.status == falcon.HTTP_201
    assert models.HouseNumber.select().count() == 1
    assert models.HouseNumber.first().postcode == postcode


@authorize
def test_replace_housenumber(client, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    assert models.HouseNumber.select().count() == 1
    uri = url('housenumber-resource', identifier=housenumber.id)
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
    assert models.HouseNumber.select().count() == 1


@authorize
def test_replace_housenumber_with_missing_field_fails(client, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    assert models.HouseNumber.select().count() == 1
    uri = url('housenumber-resource', identifier=housenumber.id)
    data = {
        "version": 2,
        "ordinal": 'bis',
        "street": housenumber.street.id,
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_422
    assert 'errors' in resp.json
    assert models.HouseNumber.select().count() == 1


@authorize
def test_patch_housenumber_with_districts(client, url):
    housenumber = HouseNumberFactory()
    district = DistrictFactory(municipality=housenumber.parent.municipality)
    data = {
        "version": 2,
        "districts": [district.id],
    }
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.patch(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_200
    hn = models.HouseNumber.get(models.HouseNumber.id == housenumber.id)
    assert district in hn.districts


@authorize
def test_patch_housenumber_with_postcode(client, url):
    postcode = PostCodeFactory(code="12345")
    housenumber = HouseNumberFactory()
    data = {
        "version": 2,
        "postcode": postcode.id,
    }
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.patch(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_200
    hn = models.HouseNumber.get(models.HouseNumber.id == housenumber.id)
    assert hn.postcode == postcode


@authorize
def test_delete_housenumber(client, url):
    housenumber = HouseNumberFactory()
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_204
    assert not models.HouseNumber.select().count()


def test_cannot_delete_housenumber_if_not_authorized(client, url):
    housenumber = HouseNumberFactory()
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_401
    assert models.HouseNumber.get(models.HouseNumber.id == housenumber.id)


@authorize
def test_cannot_delete_housenumber_if_linked_to_position(client, url):
    housenumber = HouseNumberFactory()
    PositionFactory(housenumber=housenumber)
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_409
    assert models.HouseNumber.get(models.HouseNumber.id == housenumber.id)
