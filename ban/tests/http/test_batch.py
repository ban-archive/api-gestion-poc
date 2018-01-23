from ban.core import models

from ..factories import MunicipalityFactory
from .utils import authorize

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
    assert not models.Municipality.select().count()
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