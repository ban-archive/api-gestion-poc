import json

from ban.core import models
from ban.core.encoder import dumps

from ..factories import (GroupFactory, HouseNumberFactory,
                         MunicipalityFactory, PositionFactory, PostCodeFactory)
from .utils import authorize


def test_cannot_get_housenumber_without_auth(get, url):
    resp = get(url('housenumber-resource', identifier=123))
    assert resp.status_code == 401


@authorize
def test_get_housenumber(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.status_code == 200
    assert resp.json['number'] == "22"
    assert resp.json['id'] == housenumber.id
    assert resp.json['cia'] == housenumber.cia
    assert resp.json['parent']['name'] == housenumber.parent.name


@authorize
def test_get_housenumber_without_explicit_identifier(get, url):
    housenumber = HouseNumberFactory(number="22")
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.status_code == 200
    assert resp.json['number'] == "22"
    assert resp.json['id'] == housenumber.id
    assert resp.json['cia'] == housenumber.cia
    assert resp.json['parent']['name'] == housenumber.parent.name


@authorize
def test_get_housenumber_with_unknown_id_is_404(get, url):
    resp = get(url('housenumber-resource', identifier=22))
    assert resp.status_code == 404


@authorize
def test_get_housenumber_with_cia(get, url):
    housenumber = HouseNumberFactory(number="22", parent__fantoir="900011234")
    resp = get(url('housenumber-resource', id=housenumber.cia,
                   identifier="cia"))
    assert resp.status_code == 200
    assert resp.json['number'] == "22"


@authorize
def test_get_housenumber_with_districts(get, url):
    municipality = MunicipalityFactory()
    district = GroupFactory(municipality=municipality, kind=models.Group.AREA)
    housenumber = HouseNumberFactory(ancestors=[district],
                                     municipality=municipality)
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.status_code == 200
    assert 'ancestors' in resp.json
    assert resp.json['ancestors'][0]['id'] == district.id
    assert resp.json['ancestors'][0]['name'] == district.name


@authorize
def test_get_housenumber_collection(get, url):
    objs = HouseNumberFactory.create_batch(5)
    resp = get(url('housenumber-collection'))
    assert resp.json['total'] == 5
    for obj in objs:
        assert json.loads(dumps(obj.as_relation)) in resp.json['collection']


@authorize
def test_get_housenumber_collection_can_be_filtered_by_bbox(get, url):
    position = PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2, south=0, west=0, east=2)
    resp = get(url('housenumber-collection', **bbox))
    assert resp.json['total'] == 1
    # JSON transform internals tuples to lists.
    resource = position.housenumber.as_relation
    assert resp.json['collection'][0] == json.loads(dumps(resource))


@authorize
def test_get_housenumber_bbox_allows_floats(get, url):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2.23, south=0.12, west=0.56, east=2.34)
    resp = get(url('housenumber-collection', **bbox))
    assert resp.json['total'] == 1


@authorize
def test_get_housenumber_missing_bbox_param_makes_bbox_ignored(get, url):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2, south=0, west=0)
    resp = get(url('housenumber-collection', **bbox))
    assert resp.json['total'] == 2


@authorize
def test_get_housenumber_invalid_bbox_param_returns_bad_request(get, url):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    bbox = dict(north=2, south=0, west=0, east='invalid')
    resp = get(url('housenumber-collection', **bbox))
    assert resp.status_code == 400


@authorize
def test_get_housenumber_collection_filtered_by_bbox_is_paginated(get, url):
    PositionFactory.create_batch(9, center=(1, 1))
    params = dict(north=2, south=0, west=0, east=2, limit=5)
    PositionFactory(center=(-1, -1))
    resp = get(url('housenumber-collection', **params))
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
def test_housenumber_with_two_positions_is_not_duplicated_in_bbox(get, url):
    position = PositionFactory(center=(1, 1))
    PositionFactory(center=(1.1, 1.1), housenumber=position.housenumber)
    bbox = dict(north=2, south=0, west=0, east=2)
    resp = get(url('housenumber-collection', **bbox))
    assert resp.json['total'] == 1
    # JSON transform internals tuples to lists.
    data = json.loads(dumps(position.housenumber.as_relation))
    assert resp.json['collection'][0] == data


@authorize
def test_get_housenumber_with_position(get, url):
    housenumber = HouseNumberFactory()
    position = PositionFactory(housenumber=housenumber, center=(1, 1))
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.json['positions'] == [json.loads(dumps(position.as_relation))]


@authorize
def test_get_housenumber_with_postcode(get, url):
    postcode = PostCodeFactory(code="12345")
    housenumber = HouseNumberFactory(postcode=postcode)
    resp = get(url('housenumber-resource', identifier=housenumber.id))
    assert resp.json['postcode'] == json.loads(dumps(postcode.as_relation))


@authorize
def test_get_housenumber_positions(get, url):
    housenumber = HouseNumberFactory()
    pos1 = PositionFactory(housenumber=housenumber, center=(1, 1))
    pos2 = PositionFactory(housenumber=housenumber, center=(2, 2))
    pos3 = PositionFactory(housenumber=housenumber, center=(3, 3))
    resp = get(url('position_collection', housenumber=housenumber.id))
    assert resp.json['total'] == 3

    def check(position):
        data = position.as_relation
        # postgis uses tuples for coordinates, while json does not know
        # tuple and transforms everything to lists.
        assert json.loads(dumps(data)) in resp.json['collection']

    check(pos1)
    check(pos2)
    check(pos3)


@authorize
def test_create_housenumber(client, url):
    street = GroupFactory(name="Rue de Bonbons")
    assert not models.HouseNumber.select().count()
    data = {
        "number": 20,
        "parent": street.id,
    }
    resp = client.post(url('housenumber-post'), data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['number'] == '20'
    assert resp.json['ordinal'] is None
    assert resp.json['parent']['id'] == street.id
    assert models.HouseNumber.select().count() == 1


@authorize
def test_create_housenumber_with_street_fantoir(client, url):
    street = GroupFactory(name="Rue de Bonbons", fantoir="900011234")
    assert not models.HouseNumber.select().count()
    data = {
        "number": 20,
        "parent": 'fantoir:{}'.format(street.fantoir),
    }
    resp = client.post(url('housenumber-post'), data)
    assert resp.status_code == 201
    assert models.HouseNumber.select().count() == 1


@authorize
def test_create_housenumber_does_not_honour_version_field(client, url):
    street = GroupFactory(name="Rue de Bonbons")
    data = {
        "version": 3,
        "number": 20,
        "parent": street.id,
    }
    resp = client.post(url('housenumber-post'), data=data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['version'] == 1


@authorize
def test_create_housenumber_with_postcode_id(client, url):
    postcode = PostCodeFactory(code="12345")
    street = GroupFactory(name="Rue de Bonbons")
    data = {
        "number": 20,
        "parent": street.id,
        "postcode": postcode.id
    }
    resp = client.post(url('housenumber-post'), data)
    assert resp.status_code == 201
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
        "parent": housenumber.parent.id,
    }
    resp = client.put(uri, data=data)
    assert resp.status_code == 200
    assert resp.json['id']
    assert resp.json['version'] == 2
    assert resp.json['number'] == '22'
    assert resp.json['ordinal'] == 'bis'
    assert resp.json['parent']['id'] == housenumber.parent.id
    assert models.HouseNumber.select().count() == 1


@authorize
def test_replace_housenumber_with_missing_field_fails(client, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    assert models.HouseNumber.select().count() == 1
    uri = url('housenumber-resource', identifier=housenumber.id)
    data = {
        "version": 2,
        "ordinal": 'bis',
        "street": housenumber.parent.id,
    }
    resp = client.put(uri, data=data)
    assert resp.status_code == 422
    assert 'errors' in resp.json
    assert models.HouseNumber.select().count() == 1


@authorize
def test_patch_housenumber_with_districts(client, url):
    housenumber = HouseNumberFactory()
    district = GroupFactory(municipality=housenumber.parent.municipality,
                            kind=models.Group.AREA)
    data = {
        "version": 2,
        "ancestors": [district.id],
    }
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.patch(uri, data=data)
    assert resp.status_code == 200
    hn = models.HouseNumber.get(models.HouseNumber.id == housenumber.id)
    assert district in hn.ancestors


@authorize
def test_patch_housenumber_with_postcode(client, url):
    postcode = PostCodeFactory(code="12345")
    housenumber = HouseNumberFactory()
    data = {
        "version": 2,
        "postcode": postcode.id,
    }
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.patch(uri, data=data)
    assert resp.status_code == 200
    hn = models.HouseNumber.get(models.HouseNumber.id == housenumber.id)
    assert hn.postcode == postcode


@authorize
def test_delete_housenumber(client, url):
    housenumber = HouseNumberFactory()
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.delete(uri)
    assert resp.status_code == 200
    assert resp.json['resource_id'] == housenumber.id
    assert not models.HouseNumber.select().count()


def test_cannot_delete_housenumber_if_not_authorized(client, url):
    housenumber = HouseNumberFactory()
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.delete(uri)
    assert resp.status_code == 401
    assert models.HouseNumber.get(models.HouseNumber.id == housenumber.id)


@authorize
def test_cannot_delete_housenumber_if_linked_to_position(client, url):
    housenumber = HouseNumberFactory()
    PositionFactory(housenumber=housenumber)
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.delete(uri)
    assert resp.status_code == 409
    assert models.HouseNumber.get(models.HouseNumber.id == housenumber.id)


@authorize
def test_housenumber_select_use_default_orderby(get, url):
    HouseNumberFactory(number="1", ordinal="a")
    HouseNumberFactory(number="1", ordinal="")
    HouseNumberFactory(number="2", ordinal="ter")
    HouseNumberFactory(number="2", ordinal="")
    HouseNumberFactory(number="2", ordinal="bis")
    uri = url('housenumber-collection')
    resp = get(uri)
    assert resp.status_code == 200
    assert resp.json['total'] == 5
    assert resp.json['collection'][0]['number'] == '1'
    assert resp.json['collection'][0]['ordinal'] is None
    assert resp.json['collection'][1]['number'] == '1'
    assert resp.json['collection'][1]['ordinal'] == 'a'
    assert resp.json['collection'][2]['number'] == '2'
    assert resp.json['collection'][2]['ordinal'] is None
    assert resp.json['collection'][3]['number'] == '2'
    assert resp.json['collection'][3]['ordinal'] == 'bis'
    assert resp.json['collection'][4]['number'] == '2'
    assert resp.json['collection'][4]['ordinal'] == 'ter'
