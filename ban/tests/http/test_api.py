import json

import pytest

import falcon
from ban import http
from ban.auth import models as amodels
from ban.core import models as cmodels

from ..factories import (DistrictFactory, HouseNumberFactory,
                         MunicipalityFactory, PositionFactory, PostCodeFactory,
                         StreetFactory)
from .utils import authorize

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('name,kwargs,expected', [
    ['position-resource', {"identifier": 1}, '/position/1'],
    ['position-resource', {"id": 1, "identifier": "id"}, '/position/id:1'],
    ['position', {}, '/position'],
    ['housenumber-resource', {"identifier": 1}, '/housenumber/1'],
    ['housenumber-resource', {"id": 1, "identifier": "id"}, '/housenumber/id:1'],  # noqa
    ['housenumber-resource', {"id": "93031_1491H_84_BIS", "identifier": "cia"}, '/housenumber/cia:93031_1491H_84_BIS'],  # noqa
    ['housenumber', {}, '/housenumber'],
    ['street-resource', {"identifier": 1}, '/street/1'],
    ['street-resource', {"id": 1, "identifier": "id"}, '/street/id:1'],
    ['street-resource', {"id": "930310644M", "identifier": "fantoir"}, '/street/fantoir:930310644M'],  # noqa
    ['street', {}, '/street'],
    ['municipality-resource', {"identifier": 1}, '/municipality/1'],
    ['municipality-resource', {"id": 1, "identifier": "id"}, '/municipality/id:1'],  # noqa
    ['municipality-resource', {"id": "93031", "identifier": "insee"}, '/municipality/insee:93031'],  # noqa
    ['municipality-resource', {"id": "93031321", "identifier": "siren"}, '/municipality/siren:93031321'],  # noqa
    ['municipality', {}, '/municipality'],
])
def test_api_url(name, kwargs, expected, url):
    assert url(name, **kwargs) == expected


def test_root_url_returns_api_help(get):
    resp = get('/')
    assert 'contact' in resp.json


def test_404_returns_help_as_body(get):
    resp = get('/invalid')
    assert 'contact' in resp.json


def test_help_querystring_returns_endpoint_help(get):
    resp = get('/municipality?help')
    assert 'help' in resp.json


def test_reverse_uri_are_attached_to_resource():
    assert hasattr(http.Municipality, 'root_uri')
    assert hasattr(http.Municipality, 'resource_uri')
    assert hasattr(http.Municipality, 'versions_uri')


def test_invalid_identifier_returns_404(get):
    resp = get('/position/invalid:22')
    assert resp.status == falcon.HTTP_404


def test_cors(get):
    street = StreetFactory(name="Rue des Boulets")
    resp = get('/street/id:' + str(street.id))
    assert resp.headers["Access-Control-Allow-Origin"] == "*"
    assert resp.headers["Access-Control-Allow-Headers"] == "X-Requested-With"


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


def test_get_street(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url('street-resource', id=street.id, identifier="id"))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_street_without_explicit_identifier(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url('street-resource', identifier=street.id))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_street_with_fantoir(get, url):
    street = StreetFactory(name="Rue des Boulets")
    resp = get(url('street-resource', id=street.fantoir, identifier="fantoir"))
    assert resp.json['name'] == "Rue des Boulets"


def test_get_street_housenumbers(get, url):
    street = StreetFactory()
    hn1 = HouseNumberFactory(number="1", street=street)
    hn2 = HouseNumberFactory(number="2", street=street)
    hn3 = HouseNumberFactory(number="3", street=street)
    resp = get(url('street-housenumbers', identifier=street.id))
    assert resp.json['total'] == 3
    assert resp.json['collection'][0] == hn1.as_list
    assert resp.json['collection'][1] == hn2.as_list
    assert resp.json['collection'][2] == hn3.as_list


@authorize
def test_create_housenumber(client):
    street = StreetFactory(name="Rue de Bonbons")
    assert not cmodels.HouseNumber.select().count()
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
    assert cmodels.HouseNumber.select().count() == 1


@authorize
def test_create_housenumber_with_street_fantoir(client):
    street = StreetFactory(name="Rue de Bonbons")
    assert not cmodels.HouseNumber.select().count()
    data = {
        "number": 20,
        "street": 'fantoir:{}'.format(street.fantoir),
    }
    resp = client.post('/housenumber', data)
    assert resp.status == falcon.HTTP_201
    assert cmodels.HouseNumber.select().count() == 1


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
def test_replace_housenumber(client, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    assert cmodels.HouseNumber.select().count() == 1
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
    assert cmodels.HouseNumber.select().count() == 1


@authorize
def test_replace_housenumber_with_missing_field_fails(client, url):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    assert cmodels.HouseNumber.select().count() == 1
    uri = url('housenumber-resource', identifier=housenumber.id)
    data = {
        "version": 2,
        "ordinal": 'bis',
        "street": housenumber.street.id,
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_422
    assert 'errors' in resp.json
    assert cmodels.HouseNumber.select().count() == 1


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
    hn = cmodels.HouseNumber.get(cmodels.HouseNumber.id == housenumber.id)
    assert district in hn.districts


@authorize
def test_delete_housenumber(client, url):
    housenumber = HouseNumberFactory()
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_204
    assert not cmodels.HouseNumber.select().count()


def test_cannot_delete_housenumber_if_not_authorized(client, url):
    housenumber = HouseNumberFactory()
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_401
    assert cmodels.HouseNumber.get(cmodels.HouseNumber.id == housenumber.id)


@authorize
def test_cannot_delete_housenumber_if_linked_to_position(client, url):
    housenumber = HouseNumberFactory()
    PositionFactory(housenumber=housenumber)
    uri = url('housenumber-resource', identifier=housenumber.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_409
    assert cmodels.HouseNumber.get(cmodels.HouseNumber.id == housenumber.id)


@authorize
def test_create_position(client):
    housenumber = HouseNumberFactory(number="22")
    assert not cmodels.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "housenumber": housenumber.id,
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_201
    position = cmodels.Position.first()
    assert resp.json['id'] == position.id
    assert resp.json['center']['coordinates'] == [3, 4]
    assert resp.json['housenumber']['id'] == housenumber.id


@authorize
def test_create_position_with_housenumber_cia(client):
    housenumber = HouseNumberFactory(number="22")
    assert not cmodels.Position.select().count()
    url = '/position'
    data = {
        "center": "(3, 4)",
        "housenumber": 'cia:{}'.format(housenumber.cia),
    }
    resp = client.post(url, data)
    assert resp.status == falcon.HTTP_201
    assert cmodels.Position.select().count() == 1


@authorize
def test_create_position_with_bad_housenumber_cia_is_422(client):
    HouseNumberFactory(number="22")
    assert not cmodels.Position.select().count()
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
    assert cmodels.Position.select().count() == 1
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
    assert cmodels.Position.select().count() == 1


@authorize
def test_replace_position_with_housenumber_cia(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 2,
        "center": (3, 4),
        "housenumber": 'cia:{}'.format(position.housenumber.cia)
    }
    resp = client.put(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_200
    assert cmodels.Position.select().count() == 1


@authorize
def test_replace_position_with_existing_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
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
    assert cmodels.Position.select().count() == 1


@authorize
def test_replace_position_with_non_incremental_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
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
    assert cmodels.Position.select().count() == 1


@authorize
def test_update_position(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
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
    assert cmodels.Position.select().count() == 1


@authorize
def test_update_position_with_cia(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "version": 2,
        "center": "(3.4, 5.678)",
        "housenumber": 'cia:{}'.format(position.housenumber.cia)
    }
    resp = client.post(uri, data=data)
    assert resp.status == falcon.HTTP_200
    assert cmodels.Position.select().count() == 1


@authorize
def test_update_position_with_existing_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
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
    assert cmodels.Position.select().count() == 1


@authorize
def test_update_position_with_non_incremental_version_fails(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
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
    assert cmodels.Position.select().count() == 1


@authorize
def test_patch_position_should_allow_to_update_only_some_fields(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
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
    assert cmodels.Position.select().count() == 1


@authorize
def test_patch_without_version_should_fail(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
    uri = url('position-resource', identifier=position.id)
    data = {
        "center": "(3.4, 5.678)",
    }
    resp = client.patch(uri, body=json.dumps(data))
    assert resp.status == falcon.HTTP_422


@authorize
def test_patch_with_wrong_version_should_fail(client, url):
    position = PositionFactory(source="XXX", center=(1, 2))
    assert cmodels.Position.select().count() == 1
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
    assert not cmodels.Position.select().count()


def test_cannot_delete_position_if_not_authorized(client, url):
    position = PositionFactory()
    uri = url('position-resource', identifier=position.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_401
    assert cmodels.Position.get(cmodels.Position.id == position.id)


@authorize
def test_create_street(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    assert not cmodels.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": municipality.id,
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['name'] == 'Rue de la Plage'
    assert resp.json['municipality']['id'] == municipality.id
    assert cmodels.Street.select().count() == 1
    uri = "https://falconframework.org{}".format(url('street-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_create_street_with_municipality_insee(client, url):
    municipality = MunicipalityFactory(name="Cabour")
    assert not cmodels.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "insee:{}".format(municipality.insee),
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_201
    assert cmodels.Street.select().count() == 1
    uri = "https://falconframework.org{}".format(url('street-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_create_street_with_municipality_siren(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not cmodels.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "siren:{}".format(municipality.siren),
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_201
    assert cmodels.Street.select().count() == 1


@authorize
def test_create_street_with_bad_municipality_siren(client):
    MunicipalityFactory(name="Cabour")
    assert not cmodels.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "siren:{}".format('bad'),
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_422
    assert not cmodels.Street.select().count()


@authorize
def test_create_street_with_invalid_municipality_identifier(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not cmodels.Street.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "0234H",
        "municipality": "invalid:{}".format(municipality.insee),
    }
    resp = client.post('/street', data)
    assert resp.status == falcon.HTTP_422
    assert not cmodels.Street.select().count()


def test_get_street_versions(get, url):
    street = StreetFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    uri = url('street-versions', identifier=street.id)
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
    uri = url('street-version', identifier=street.id, version=1)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Rue de la Paix'
    assert resp.json['version'] == 1
    uri = url('street-version', identifier=street.id, version=2)
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['name'] == 'Rue de la Guerre'
    assert resp.json['version'] == 2


def test_get_street_unknown_version_should_go_in_404(get, url):
    street = StreetFactory(name="Rue de la Paix")
    uri = url('street-version', identifier=street.id, version=2)
    resp = get(uri)
    assert resp.status == falcon.HTTP_404


@authorize
def test_delete_street(client, url):
    street = StreetFactory()
    uri = url('street-resource', identifier=street.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_204
    assert not cmodels.Street.select().count()


def test_cannot_delete_street_if_not_authorized(client, url):
    street = StreetFactory()
    uri = url('street-resource', identifier=street.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_401
    assert cmodels.Street.get(cmodels.Street.id == street.id)


@authorize
def test_cannot_delete_street_if_linked_to_housenumber(client, url):
    street = StreetFactory()
    HouseNumberFactory(street=street)
    uri = url('street-resource', identifier=street.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_409
    assert cmodels.Street.get(cmodels.Street.id == street.id)


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
    assert not cmodels.Municipality.select().count()
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
    }
    resp = client.post(url('municipality'), data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['name'] == 'Fornex'
    assert cmodels.Municipality.select().count() == 1
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
    municipality = cmodels.Municipality.first()
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
    municipality = cmodels.Municipality.first()
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
    municipality = cmodels.Municipality.first()
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
    municipality = cmodels.Municipality.first()
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
    municipality = cmodels.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias


@authorize
def test_delete_municipality(client, url):
    municipality = MunicipalityFactory()
    uri = url('municipality-resource', identifier=municipality.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_204
    assert not cmodels.Municipality.select().count()


def test_cannot_delete_municipality_if_not_authorized(client, url):
    municipality = MunicipalityFactory()
    uri = url('municipality-resource', identifier=municipality.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_401
    assert cmodels.Municipality.get(cmodels.Municipality.id == municipality.id)


@authorize
def test_cannot_delete_municipality_if_linked_to_street(client, url):
    municipality = MunicipalityFactory()
    StreetFactory(municipality=municipality)
    uri = url('municipality-resource', identifier=municipality.id)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_409
    assert cmodels.Municipality.get(cmodels.Municipality.id == municipality.id)


@authorize
def test_delete_unknown_municipality_should_return_not_found(client, url):
    uri = url('municipality-resource', identifier=11)
    resp = client.delete(uri)
    assert resp.status == falcon.HTTP_404


def test_get_district(get, url):
    district = DistrictFactory(name="Lhomme")
    resp = get(url('district-resource', identifier=district.id))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['name'] == 'Lhomme'
    assert resp.json['municipality']['id'] == district.municipality.id


@authorize
def test_create_district(client, url):
    assert not cmodels.District.select().count()
    municipality = MunicipalityFactory()
    data = {
        "name": "Lhomme",
        "attributes": {"key": "value"},
        "municipality": municipality.id
    }
    # As attributes is a dict, we need to send form as json.
    headers = {'Content-Type': 'application/json'}
    resp = client.post(url('district'), json.dumps(data), headers=headers)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['name'] == 'Lhomme'
    assert resp.json['attributes'] == {"key": "value"}
    assert cmodels.District.select().count() == 1
    uri = "https://falconframework.org{}".format(url('district-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_create_district_with_json_string_as_attribute(client, url):
    assert not cmodels.District.select().count()
    municipality = MunicipalityFactory()
    data = {
        "name": "Lhomme",
        "attributes": json.dumps({"key": "value"}),
        "municipality": municipality.id
    }
    resp = client.post(url('district'), data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['attributes'] == {"key": "value"}


def test_get_postcode(get, url):
    postcode = PostCodeFactory(code="09350")
    resp = get(url('postcode-resource', identifier=postcode.id))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['code'] == '09350'


def test_get_postcode_with_code(get, url):
    PostCodeFactory(code="09350")
    resp = get(url('postcode-resource', identifier='code:09350'))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['code'] == '09350'


@authorize
def test_create_postcode(client, url):
    assert not cmodels.PostCode.select().count()
    data = {
        "code": "09350"
    }
    resp = client.post(url('postcode'), data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['code'] == '09350'
    assert cmodels.PostCode.select().count() == 1
    uri = "https://falconframework.org{}".format(url('postcode-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_create_user(client, url):
    # Client user + session user == 2
    assert amodels.User.select().count() == 2
    resp = client.post('/user', {
        'username': 'newuser',
        'email': 'test@test.com',
    })
    assert resp.status == falcon.HTTP_201
    assert amodels.User.select().count() == 3
    uri = "https://falconframework.org{}".format(url('user-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_cannot_create_user_without_username(client):
    assert amodels.User.select().count() == 2
    resp = client.post('/user', {
        'username': '',
        'email': 'test@test.com',
    })
    assert resp.status == falcon.HTTP_422
    assert amodels.User.select().count() == 2


@authorize
def test_cannot_create_user_without_email(client):
    assert amodels.User.select().count() == 2
    resp = client.post('/user', {
        'username': 'newuser',
        'email': '',
    })
    assert resp.status == falcon.HTTP_422
    assert amodels.User.select().count() == 2


def test_cannot_create_user_if_not_authenticated(client):
    assert not amodels.User.select().count()
    resp = client.post('/user', {
        'username': 'newuser',
        'email': 'test@test.com',
    })
    assert resp.status == falcon.HTTP_401
    assert not amodels.User.select().count()
