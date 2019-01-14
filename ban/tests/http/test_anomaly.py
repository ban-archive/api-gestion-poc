import json

from ban.core import models, versioning
from ban.core.encoder import dumps

from ..factories import AnomalyFactory, HouseNumberFactory, VersionFactory, GroupFactory
from .utils import authorize


def test_cannot_get_anomaly_without_auth(get):
    resp = get('/anomaly')
    assert resp.status_code == 401


@authorize
def test_get_anomaly(get):
    anomaly = AnomalyFactory(kind="hn vide")
    resp = get('/anomaly'.format(anomaly.id))
    assert resp.status_code == 200
    assert resp.json["total"] == 1


@authorize
def test_get_anomaly_by_id(get):
    anomaly = AnomalyFactory(kind="hn vide")
    resp = get('/anomaly/{}'.format(anomaly.id))
    assert resp.status_code == 200
    assert resp.json["kind"] == "hn vide"


@authorize
def test_get_anomalies_by_kind(get):
    a1 = AnomalyFactory(kind="hn vide")
    a2 = AnomalyFactory(kind="hn vide")
    resp = get('/anomaly?kind=hn+vide')
    assert resp.status_code == 200
    assert resp.json["total"] == 2


@authorize
def test_get_anomaly_by_version(get):
    h = HouseNumberFactory()
    v = VersionFactory(model_pk=h.pk, data='{"nom":"test"}')
    a = AnomalyFactory(versions = [v])
    a2 = AnomalyFactory()
    resp = get('/anomaly?resource={}&version={}'.format(h.id, v.sequential))
    assert resp.status_code == 200
    assert resp.json["total"] == 1
    assert resp.json["collection"][0]["versions"][0]["data"]== '{"nom":"test"}'


@authorize('anomaly_write')
def test_create_anomaly(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "insee": "33544",
        "versions": [{"version":street.version, "id":street.id, "resource":"group"}],
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['kind'] == 'nom vide'
    assert resp.json['insee'] == '33544'
    assert resp.json['versions'][0]['data']


@authorize
def test_cannot_create_anomaly_without_scopes(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "insee": "33544",
        "versions": [{"version":street.version, "id":street.id, "resource":"group"}],
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 401


@authorize('anomaly_write')
def test_cannot_create_anomaly_without_kind(client):
    street = GroupFactory()
    data = {
        "insee": "33544",
        "versions": [{"version":street.version, "id":street.id, "resource":"group"}],
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 422


@authorize('anomaly_write')
def test_cannot_create_anomaly_without_insee(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "versions": [{"version":street.version, "id":street.id, "resource":"group"}],
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 422


@authorize('anomaly_write')
def test_cannot_create_anomaly_without_versions(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "insee": "33544",
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 422


@authorize('anomaly_write')
def test_cannot_create_anomaly_with_empty_versions(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "insee": "33544",
        "versions": []
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 422


@authorize('anomaly_write')
def test_cannot_create_anomaly_with_bad_versions(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "insee": "33544",
        "versions": [{"bad":"version"}]
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 422


@authorize('anomaly_write')
def test_cannot_create_anomaly_without_resource(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "insee": "33544",
        "versions": [{"version":street.version, "id":street.id}],
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 422


@authorize('anomaly_write')
def test_cannot_create_anomaly_with_bad_resource(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "insee": "33544",
        "versions": [{"version":street.version, "id":street.id, "resource":"coucou"}],
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 422


@authorize('anomaly_write')
def test_cannot_create_anomaly_with_bad_id(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "insee": "33544",
        "versions": [{"version":street.version, "id":"coucou", "resource":"group"}],
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 404


@authorize('anomaly_write')
def test_cannot_create_anomaly_with_bad_version(client):
    street = GroupFactory()
    data = {
        "kind": "nom vide",
        "insee": "33544",
        "versions": [{"version":"9", "id":street.id, "resource":"group"}],
    }
    resp = client.post('/anomaly', data)
    assert resp.status_code == 422


@authorize('anomaly_write')
def test_put_anomaly(client):
    h = HouseNumberFactory()
    v = VersionFactory(model_pk=h.pk, data='{"nom":"test"}')
    a = AnomalyFactory(versions = [v], kind="number vide")
    data = {
        "kind": "hn 5000",
        "insee": "33544",
        "versions": [{"version":h.version, "id":h.id, "resource":"housenumber"}],
    }
    resp = client.put('/anomaly/{}'.format(a.id), data)
    assert resp.status_code == 200
    a2 = versioning.Anomaly.get(versioning.Anomaly.id==a.id)
    assert a2.kind == 'hn 5000'


@authorize('anomaly_write')
def test_patch_anomaly(client):
    h = HouseNumberFactory()
    v = VersionFactory(model_pk=h.pk, data='{"nom":"test"}')
    a = AnomalyFactory(versions = [v], kind="number vide")
    data = {
        "kind": "hn 5000"
    }
    resp = client.patch('/anomaly/{}'.format(a.id), data)
    assert resp.status_code == 200
    a2 = versioning.Anomaly.get(versioning.Anomaly.id==a.id)
    assert a2.kind == 'hn 5000'


@authorize('anomaly_write')
def test_delete_anomaly(client):
    h = HouseNumberFactory()
    v = VersionFactory(model_pk=h.pk, data='{"nom":"test"}')
    a = AnomalyFactory(versions = [v], kind="number vide")
    resp = client.delete('/anomaly/{}'.format(a.id))
    assert resp.status_code == 204
    a2 = versioning.Anomaly.select().where(versioning.Anomaly.id==a.id).first()
    assert a2 is None

