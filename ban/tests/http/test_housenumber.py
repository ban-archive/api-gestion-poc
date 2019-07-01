import json

from ban.core import models
from ban.core.encoder import dumps

from ..factories import (GroupFactory, HouseNumberFactory,
                         MunicipalityFactory, PositionFactory, PostCodeFactory)
from .utils import authorize


def test_cannot_get_housenumber_without_auth(get):
    resp = get('/housenumber/123')
    assert resp.status_code == 401


@authorize
def test_get_housenumber(get):
    housenumber = HouseNumberFactory(number="22")
    resp = get('/housenumber/{}'.format(housenumber.id))
    assert resp.status_code == 200
    assert resp.json == {
        'number': '22',
        'id': housenumber.id,
        'cia': housenumber.cia,
        'parent': housenumber.parent.id,
        'version': 1,
        'modified_at': housenumber.modified_at.isoformat(),
        'created_at': housenumber.created_at.isoformat(),
        'modified_by': housenumber.modified_by.serialize(),
        'created_by': housenumber.created_by.serialize(),
        'ancestors': [],
        'attributes': None,
        'ign': None,
        'laposte': None,
        'ordinal': 'bis',
        'postcode': None,
        'status': 'active',
        'positions': []
    }
#

@authorize
def test_get_housenumber_with_filtered_fields(get):
    housenumber = HouseNumberFactory(number="22")
    resp = get('/housenumber/{}?fields=number,id'.format(housenumber.id))
    assert resp.status_code == 200
    assert resp.json == {
        'number': '22',
        'id': housenumber.id,
    }


@authorize
def test_get_housenumber_with_filtered_parent_fields(get):
    housenumber = HouseNumberFactory(number="22")
    resp = get('/housenumber/{}?fields=id,parent.name'.format(housenumber.id))
    assert resp.status_code == 200
    assert resp.json == {
        'id': housenumber.id,
        'parent': {
            'name': housenumber.parent.name
        }
    }


@authorize
def test_get_housenumber_with_filtered_municipality_fields(get):
    housenumber = HouseNumberFactory(number="22")
    fields = 'id,parent.name,parent.municipality.name'
    resp = get('/housenumber/{}?fields={}'.format(housenumber.id, fields))
    assert resp.status_code == 200
    assert resp.json == {
        'id': housenumber.id,
        'parent': {
            'name': housenumber.parent.name,
            'municipality': {
                'name': housenumber.parent.municipality.name
            }
        }
    }


@authorize
def test_get_housenumber_without_explicit_identifier(get):
    housenumber = HouseNumberFactory(number="22")
    resp = get('/housenumber/{}'.format(housenumber.id))
    assert resp.status_code == 200
    assert resp.json['number'] == "22"
    assert resp.json['id'] == housenumber.id
    assert resp.json['cia'] == housenumber.cia
    assert resp.json['parent'] == housenumber.parent.id


@authorize
def test_get_housenumber_with_unknown_id_is_404(get):
    resp = get('/housenumber/{}'.format(22))
    assert resp.status_code == 404


@authorize
def test_get_housenumber_with_cia(get):
    housenumber = HouseNumberFactory(number="22", parent__fantoir="900011234")
    resp = get('/housenumber/cia:{}'.format(housenumber.cia))
    assert resp.status_code == 200
    assert resp.json['number'] == "22"

@authorize
def test_get_housenumber_with_number(get):
    housenumber = HouseNumberFactory(number="22")
    resp = get('/housenumber?number=22')
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 1

@authorize
def test_get_housenumber_with_group_number(get):
    municipality = MunicipalityFactory()
    area = GroupFactory(municipality=municipality, kind=models.Group.AREA)
    housenumber = HouseNumberFactory(parent=area, number="22")
    resp = get('/housenumber?group={}&number=22'.format(area.id))
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 1

@authorize
def test_get_housenumber_with_bad_group(get):
    housenumber = HouseNumberFactory(number="22")
    resp = get('/housenumber?group=6666')
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 0

@authorize
def test_get_housenumber_with_bad_number(get):
    housenumber = HouseNumberFactory(number="22")
    resp = get('/housenumber?number=23')
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 0

@authorize
def test_get_housenumber_with_ordinal(get):
    housenumber = HouseNumberFactory(ordinal="BIS")
    resp = get('/housenumber?ordinal=BIS')
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 1

@authorize
def test_get_housenumber_with_bad_ordinal(get):
    housenumber = HouseNumberFactory(number="TER", ordinal="Z")
    resp = get('/housenumber?ordinal=BIS')
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 0

@authorize
def test_get_housenumber_with_number_ordinal(get):
    housenumber = HouseNumberFactory(number="22", ordinal="BIS")
    resp = get('/housenumber?number=22&ordinal=bis')
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 1

@authorize
def test_get_housenumber_with_districts(get):
    municipality = MunicipalityFactory()
    district = GroupFactory(municipality=municipality, kind=models.Group.AREA)
    housenumber = HouseNumberFactory(ancestors=[district],
                                     parent__municipality=municipality)
    resp = get('/housenumber/{}'.format(housenumber.id))
    assert resp.status_code == 200
    assert 'ancestors' in resp.json
    assert resp.json['ancestors'][0] == district.id

@authorize
def test_get_housenumber_with_ancestors(get):
    municipality = MunicipalityFactory()
    ancestor = GroupFactory(municipality=municipality, kind=models.Group.AREA)
    housenumber = HouseNumberFactory(ancestors=[ancestor],
                                     parent__municipality=municipality)
    resp = get('/housenumber?ancestors={}'.format(ancestor.id))
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 1

@authorize
def test_get_housenumber_with_ancestors(get):
    municipality = MunicipalityFactory()
    ancestor = GroupFactory(municipality=municipality, kind=models.Group.AREA)
    housenumber = HouseNumberFactory(number="22", ancestors=[ancestor],
                                     parent__municipality=municipality)
    resp = get('/housenumber?ancestors={}&number=22'.format(ancestor.id))
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 1

@authorize
def test_get_housenumber_collection(get):
    objs = HouseNumberFactory.create_batch(5)
    resp = get('/housenumber')
    assert len(resp.json['collection']) == 5


@authorize
def test_get_housenumber_collection_can_be_filtered_by_bbox(get):
    position = PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    resp = get('/housenumber?north=2&south=0&west=0&east=2')
    assert len(resp.json['collection']) == 1


@authorize
def test_get_housenumber_bbox_allows_floats(get):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    resp = get('/housenumber?north=2.23&south=0.12&west=0.56&east=2.34')
    assert len(resp.json['collection']) == 1


@authorize
def test_get_housenumber_missing_bbox_param_makes_bbox_ignored(get):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    resp = get('/housenumber?north=1&south=0&west=0')
    assert len(resp.json['collection']) == 2


@authorize
def test_get_housenumber_invalid_bbox_param_returns_bad_request(get):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    resp = get('/housenumber?north=2&south=0&west=0&east=invalid')
    assert resp.status_code == 400


@authorize
def test_get_housenumber_collection_filtered_by_bbox_is_paginated(get):
    PositionFactory.create_batch(9, center=(1, 1))
    PositionFactory(center=(-1, -1))
    resp = get('/housenumber?north=2&south=0&west=0&east=2&limit=5')
    page1 = resp.json
    assert len(page1['collection']) == 5
    assert 'next' in page1
    assert 'previous' not in page1
    resp = get(page1['next'])
    page2 = resp.json
    assert len(page2['collection']) == 4
    assert 'previous' in page2
    resp = get(page2['previous'])
    assert resp.json == page1


@authorize
def test_housenumber_with_two_positions_is_not_duplicated_in_bbox(get):
    position = PositionFactory(center=(1, 1))
    PositionFactory(center=(1.1, 1.1), housenumber=position.housenumber)
    resp = get('/housenumber?north=2&south=0&west=0&east=2')
    assert len(resp.json['collection']) == 1



@authorize
def test_get_housenumber_with_postcode(get):
    postcode = PostCodeFactory(code="12345")
    housenumber = HouseNumberFactory(postcode=postcode)
    resp = get('/housenumber/{}'.format(housenumber.id))
    assert resp.json['postcode'] == postcode.id


@authorize
def test_get_housenumber_positions(get):
    housenumber = HouseNumberFactory()
    pos1 = PositionFactory(housenumber=housenumber, center=(1, 1))
    pos2 = PositionFactory(housenumber=housenumber, center=(2, 2))
    pos3 = PositionFactory(housenumber=housenumber, center=(3, 3))
    resp = get('/position?housenumber={}'.format(housenumber.id))
    assert len(resp.json['collection']) == 3


@authorize
def test_get_housenumber_deleted(get):
    housenumber = HouseNumberFactory()
    housenumber.mark_deleted()
    resp = get('/housenumber/{}'.format(housenumber.id))
    assert resp.status_code == 410
    assert resp.json['id'] == housenumber.id
    assert len(housenumber.versions) == 2
    assert resp.json['status'] == 'deleted'


@authorize
def test_get_housenumber_deleted_on_group_deleted(client):
    group = GroupFactory()
    housenumber = HouseNumberFactory(number='1', ordinal='bis', parent=group)
    housenumber.mark_deleted()
    group.mark_deleted()
    resp = client.get('/housenumber/{}'.format(housenumber.id))
    assert resp.status_code == 410
    assert resp.json['id'] == housenumber.id
    assert len(housenumber.versions) == 2
    assert resp.json['status'] == 'deleted'


@authorize('housenumber_write')
def test_create_housenumber(client):
    street = GroupFactory(name="Rue de Bonbons")
    assert not models.HouseNumber.select().count()
    data = {
        "number": 20,
        "parent": street.id
    }
    resp = client.post('/housenumber', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['number'] == '20'
    assert resp.json['ordinal'] is None
    assert resp.json['parent'] == street.id
    assert models.HouseNumber.select().count() == 1


@authorize('housenumber_write')
def test_create_housenumber_with_street_fantoir(client):
    street = GroupFactory(name="Rue de Bonbons", fantoir="900011234")
    assert not models.HouseNumber.select().count()
    data = {
        "number": 20,
        "parent": 'fantoir:{}'.format(street.fantoir),
    }
    resp = client.post('/housenumber', data)
    assert resp.status_code == 201
    assert models.HouseNumber.select().count() == 1


@authorize('housenumber_write')
def create_housenumber_reactivation(client):
    housenumber = HouseNumberFactory()
    housenumber.mark_deleted()
    data = {
        "number": housenumber.number,
        "ordinal": housenumber.ordinal,
        "parent": housenumber.parent.id
    }
    resp = client.post('/housenumber', data)
    assert resp.status_code == 200
    assert resp.json['id'] == housenumber.id
    assert resp.json['version'] == 3
    assert resp.json['status'] == 'active'


@authorize('housenumber_write')
def test_create_housenumber_does_not_honour_version_field(client):
    street = GroupFactory(name="Rue de Bonbons")
    data = {
        "version": 3,
        "number": 20,
        "parent": street.id,
    }
    resp = client.post('/housenumber', data=data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['version'] == 1


@authorize('housenumber_write')
def test_create_housenumber_with_postcode_id(client):
    postcode = PostCodeFactory(code="12345")
    street = GroupFactory(name="Rue de Bonbons")
    data = {
        "number": 20,
        "parent": street.id,
        "postcode": postcode.id
    }
    resp = client.post('/housenumber', data)
    assert resp.status_code == 201
    assert models.HouseNumber.select().count() == 1
    assert models.HouseNumber.first().postcode == postcode


@authorize('housenumber_write')
def test_create_housenumber_on_deleted_group(client):
    deleted = GroupFactory()
    deleted.mark_deleted()
    assert not models.HouseNumber.select().count()
    data = {
        "number": 20,
        "parent": deleted.id,
    }
    resp = client.post('/housenumber', data)
    assert resp.status_code == 422
    assert resp.json['errors']['parent'] == (
        'Resource `group` with id `{}` is deleted'.format(deleted.id))


@authorize('housenumber_write')
def test_create_housenumber_on_deleted_ancestor(client):
    group = GroupFactory()
    deleted = GroupFactory()
    deleted.mark_deleted()
    assert not models.HouseNumber.select().count()
    data = {
        "number": 20,
        "parent": group.id,
        "ancestors": [deleted.id],
    }
    resp = client.post('/housenumber', data)
    assert resp.status_code == 422
    assert resp.json['errors']['ancestors'] == (
        'Resource `group` with id `{}` is deleted'.format(deleted.id))


@authorize('housenumber_write')
def test_empty_body_should_not_crash(client):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    assert models.HouseNumber.select().count() == 1
    uri = '/housenumber/{}'.format(housenumber.id)
    resp = client.put(uri, data=None)
    assert resp.status_code == 422


@authorize('housenumber_write')
def test_replace_housenumber(client):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    assert models.HouseNumber.select().count() == 1
    uri = '/housenumber/{}'.format(housenumber.id)
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
    assert resp.json['parent'] == housenumber.parent.id
    assert models.HouseNumber.select().count() == 1


@authorize('housenumber_write')
def test_replace_housenumber_with_missing_field_fails(client):
    housenumber = HouseNumberFactory(number="22", ordinal="B")
    assert models.HouseNumber.select().count() == 1
    uri = '/housenumber/{}'.format(housenumber.id)
    data = {
        "version": 2,
        "ordinal": 'bis',
        "street": housenumber.parent.id,
    }
    resp = client.put(uri, data=data)
    assert resp.status_code == 422
    assert resp.json['error'] == 'Invalid data'
    assert 'errors' in resp.json
    assert models.HouseNumber.select().count() == 1


@authorize('housenumber_write')
def test_patch_housenumber_with_districts(client):
    housenumber = HouseNumberFactory()
    district = GroupFactory(municipality=housenumber.parent.municipality,
                            kind=models.Group.AREA)
    data = {
        "version": 2,
        "ancestors": [district.id],
    }
    uri = '/housenumber/{}'.format(housenumber.id)
    resp = client.patch(uri, data=data)
    assert resp.status_code == 200
    hn = models.HouseNumber.get(models.HouseNumber.id == housenumber.id)
    assert district in hn.ancestors


@authorize('housenumber_write')
def test_patch_housenumber_doublon_number_ordinal_parent(client):
    group = GroupFactory()
    housenumber1 = HouseNumberFactory(number='1', ordinal='bis', parent=group)
    housenumber2 = HouseNumberFactory(number='1', ordinal=None, parent=group)
    data = {
        "version": 2,
        "ordinal": "",
    }
    uri = '/housenumber/{}'.format(housenumber1.id)
    resp = client.patch(uri, data=data)
    assert resp.status_code == 422


@authorize('housenumber_write')
def test_patch_housenumber_vidage_ign(client):
    group = GroupFactory()
    housenumber1 = HouseNumberFactory(number='1', ordinal=None, parent=group)
    housenumber2 = HouseNumberFactory(number='2', ordinal=None, parent=group)
    data = {
        "version": 2,
        "number": "3",
    }
    uri = '/housenumber/{}'.format(housenumber1.id)
    resp = client.patch(uri, data=data)
    assert resp.status_code == 200


@authorize('housenumber_write')
def test_patch_housenumber_with_postcode(client):
    postcode = PostCodeFactory(code="12345")
    housenumber = HouseNumberFactory()
    data = {
        "version": 2,
        "postcode": postcode.id,
    }
    uri = '/housenumber/{}'.format(housenumber.id)
    resp = client.patch(uri, data=data)
    assert resp.status_code == 200
    hn = models.HouseNumber.get(models.HouseNumber.id == housenumber.id)
    assert hn.postcode == postcode


@authorize('housenumber_write')
def test_delete_housenumber(client):
    housenumber = HouseNumberFactory()
    uri = '/housenumber/{}'.format(housenumber.id)
    resp = client.delete(uri)
    assert resp.status_code == 204
    assert models.HouseNumber.select().count() == 1
    assert models.HouseNumber.raw_select().where(
                    models.HouseNumber.pk == housenumber.pk).get().deleted_at


def test_cannot_delete_housenumber_if_not_authorized(client):
    housenumber = HouseNumberFactory()
    uri = '/housenumber/{}'.format(housenumber.id)
    resp = client.delete(uri)
    assert resp.status_code == 401
    assert models.HouseNumber.get(models.HouseNumber.id == housenumber.id)


@authorize('housenumber_foo')
def test_cannot_delete_housenumber_without_correct_scope(client):
    housenumber = HouseNumberFactory()
    uri = '/housenumber/{}'.format(housenumber.id)
    resp = client.delete(uri)
    assert resp.status_code == 401
    assert models.HouseNumber.get(models.HouseNumber.id == housenumber.id)


@authorize('housenumber_write')
def test_cannot_delete_housenumber_if_linked_to_position(client):
    housenumber = HouseNumberFactory()
    PositionFactory(housenumber=housenumber)
    uri = '/housenumber/{}'.format(housenumber.id)
    resp = client.delete(uri)
    assert resp.status_code == 409
    assert models.HouseNumber.get(models.HouseNumber.id == housenumber.id)


@authorize
def test_housenumber_select_use_default_orderby(get):
    HouseNumberFactory(number="1", ordinal="a")
    HouseNumberFactory(number="1", ordinal="")
    HouseNumberFactory(number="2", ordinal="ter")
    HouseNumberFactory(number="2", ordinal="")
    HouseNumberFactory(number="2", ordinal="bis")
    resp = get('/housenumber')
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 5
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


@authorize('housenumber_write')
def test_cannot_duplicate_number_and_ordinal_for_same_parent(client):
    assert not models.HouseNumber.select().count()
    housenumber = HouseNumberFactory(number='4', ordinal='bis')
    data = {
        "number": "4",
        "ordinal": "bis",
        "parent": housenumber.parent.id,
    }
    resp = client.post('/housenumber', data)
    assert resp.status_code == 422
    assert models.HouseNumber.select().count() == 1
    assert 'number' in resp.json['errors']
    assert 'ordinal' in resp.json['errors']
    assert 'parent' in resp.json['errors']


@authorize('housenumber_write')
def test_cannot_duplicate_number_with_empty_ordinal_for_same_parent(client):
    assert not models.HouseNumber.select().count()
    housenumber = HouseNumberFactory(number='4', ordinal=None)
    data = {
        "number": "4",
        "parent": housenumber.parent.id,
    }
    resp = client.post('/housenumber', data)
    assert resp.status_code == 422
    assert models.HouseNumber.select().count() == 1
    assert 'number' in resp.json['errors']
    assert 'ordinal' in resp.json['errors']
    assert 'parent' in resp.json['errors']


@authorize('housenumber_write')
def test_cannot_create_housenumber_case_doublon_number_ordinal_parent(client):
    assert not models.HouseNumber.select().count()
    housenumber = HouseNumberFactory(number='1', ordinal='bis')
    data = {
        "number": "1",
        "ordinal": "BIS",
        "parent": housenumber.parent.id
    }
    resp = client.post('/housenumber', data)
    assert resp.status_code == 422
    assert models.HouseNumber.select().count() == 1
    assert 'number' in resp.json['errors']
    assert 'ordinal' in resp.json['errors']
    assert 'parent' in resp.json['errors']
