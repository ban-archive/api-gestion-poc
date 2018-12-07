from ban.core import models

from ..factories import MunicipalityFactory, GroupFactory, HouseNumberFactory
from .utils import authorize


@authorize
def test_batch_no_data(post):
    data = []
    resp = post('/batch', data)
    assert resp.status_code == 400


@authorize
def test_batch_no_method(post):
    data = [{
        "path":"/municipality",
        "body": {
            "name": "Fornex",
            "insee": "12345",
            "siren": '123456789'
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 422


@authorize
def test_batch_no_path(post):
    data = [{
        "method": "POST",
        "body": {
            "name": "Fornex",
            "insee": "12345",
            "siren": '123456789'
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 422


@authorize
def test_batch_post_municipality_no_body(post):
    data = [{
        "path":"/municipality",
        "method": "POST",
        "body": {}
    }]
    resp = post('/batch', data)
    assert resp.status_code == 422


@authorize('municipality_write')
def test_batch_wrong_method(post):
    data = [{
        "path": "/municipality",
        "method": "POTS",
        "body": {
            "name": "Fornex",
            "insee": "12345",
            "siren": '123456789'
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 422


@authorize
def test_batch_wrong_path(post):
    data = [{
        "path": "coucou",
        "method": "POST",
        "body": {
            "name": "Fornex",
            "insee": "12345",
            "siren": '123456789'
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 422


@authorize('municipality_write')
def test_batch_post_municipality(post):
    assert not models.Municipality.select().count()
    data = [{
        "method": "POST",
        "path": "/municipality",
        "body": {
            "name": "Fornex",
            "insee": "12345",
            "siren": '123456789'
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['name'] == 'Fornex'
    assert models.Municipality.select().count() == 1
    uri = 'http://localhost/municipality/{}'.format(resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize('postcode_write')
def test_batch_post_postcode(post):
    municipality = MunicipalityFactory()
    data = [{
        "method": "POST",
        "path": "/postcode",
        "body": {
            "name": "Fornex",
            "code": "12345",
            "municipality": municipality.id
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['name'] == 'Fornex'
    assert models.PostCode.select().count() == 1
    uri = 'http://localhost/postcode/{}'.format(resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize('group_write')
def test_batch_post_group(post):
    municipality = MunicipalityFactory()
    data = [{
        "method": "POST",
        "path": "/group",
        "body": {
            "name": "Rue des lilas",
            "kind": models.Group.WAY,
            "municipality": municipality.id
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['name'] == 'Rue des lilas'
    assert models.Group.select().count() == 1
    uri = 'http://localhost/group/{}'.format(resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize('housenumber_write')
def test_batch_post_housenumber(post):
    group = GroupFactory()
    data = [{
        "method": "POST",
        "path": "/housenumber",
        "body": {
            "number": "1",
            "parent": group.id
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['number'] == '1'
    assert models.HouseNumber.select().count() == 1
    uri = 'http://localhost/housenumber/{}'.format(resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize('position_write')
def test_batch_post_position(post):
    housenumber = HouseNumberFactory()
    data = [{
        "method": "POST",
        "path": "/position",
        "body": {
            "center": "(3, 4)",
            "positioning": models.Position.GPS,
            "kind": models.Position.ENTRANCE,
            "housenumber": housenumber.id
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert models.Position.select().count() == 1
    uri = 'http://localhost/position/{}'.format(resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize('municipality_write')
def test_batch_patch_municipality(post):
    municipality = MunicipalityFactory()
    data = [{
        "method": "PATCH",
        "path": "/municipality/{}".format(municipality.id),
        "body": {
            "version": 2,
            "alias": ['Moret-sur-Loing']
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 200
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias


@authorize('municipality_write')
def test_batch_delete_municipality(post):
    municipality = MunicipalityFactory()
    data = [{"method": "DELETE",
             "path": "/municipality/{}".format(municipality.id),
    }]
    resp = post('/batch', data)
    assert resp.status_code == 200
    assert resp.json['resource_id'] == municipality.id
    assert models.Municipality.select().count() == 1
    assert models.Municipality.raw_select().where(
                models.Municipality.pk == municipality.pk).first().deleted_at


@authorize
def test_batch_post_municipality_without_scopes(post):
    data = [{
        "method": "POST",
        "path": "/municipality",
        "body":{
            "name": "Fornex",
            "insee": "12345",
            "siren": '123456789'
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 401


@authorize('municipality_write')
def test_batch_rollback_error(post):
    assert not models.Municipality.select().count()
    data = [{
        "method": "POST",
        "path": "/municipality",
        "body": {
            "name": "Fornex",
            "insee": "12345",
            "siren": '123456789'
        }
    },
    {
        "method": "POST",
        "path": "/municipality",
        "body": {
            "name": "Fornex",
            "insee": "12345",
            "siren": '123456789'
        }
    }]
    resp = post('/batch', data)
    assert resp.status_code == 422
    assert models.Municipality.select().count() == 0
