import json

from ban.core import models
from ban.core.encoder import dumps

from ..factories import HouseNumberFactory, MunicipalityFactory, GroupFactory
from .utils import authorize


def test_cannot_get_group_without_auth(get):
    resp = get('/group/123')
    assert resp.status_code == 401


@authorize
def test_get_group(get):
    street = GroupFactory(name="Rue des Boulets")
    resp = get('/group/{}'.format(street.id))
    assert resp.status_code == 200
    assert resp.json['name'] == "Rue des Boulets"


@authorize
def test_get_group_without_explicit_identifier(get):
    street = GroupFactory(name="Rue des Boulets")
    resp = get('/group/{}'.format(street.id))
    assert resp.status_code == 200
    assert resp.json['name'] == "Rue des Boulets"


@authorize
def test_get_group_with_fantoir(get):
    street = GroupFactory(name="Rue des Boulets", fantoir='900011234')
    resp = get('/group/fantoir:{}'.format(street.fantoir))
    assert resp.status_code == 200
    assert resp.json['name'] == "Rue des Boulets"


@authorize
def test_get_group_with_pk(get):
    street = GroupFactory(name="Rue des Boulets")
    resp = get('/group/pk:{}'.format(street.pk))
    assert resp.status_code == 200
    assert resp.json['name'] == "Rue des Boulets"


@authorize
def test_get_group_housenumbers(get):
    street = GroupFactory()
    hn1 = HouseNumberFactory(number="1", parent=street)
    hn2 = HouseNumberFactory(number="2", parent=street)
    hn3 = HouseNumberFactory(number="3", parent=street)
    resp = get('/housenumber?group={}'.format(street.id))
    assert resp.status_code == 200
    assert resp.json['total'] == 3
    assert resp.json['collection'][0] == json.loads(dumps({
        'attributes': None,
        'laposte': None,
        'ordinal': 'bis',
        'parent': street.id,
        'id': hn1.id,
        'version': 1,
        'postcode': None,
        'number': '1',
        'resource': 'housenumber',
        'cia': hn1.cia,
        'ign': None,
    }))
    assert resp.json['collection'][1] == json.loads(dumps({
        'attributes': None,
        'laposte': None,
        'ordinal': 'bis',
        'parent': street.id,
        'id': hn2.id,
        'version': 1,
        'postcode': None,
        'number': '2',
        'resource': 'housenumber',
        'cia': hn2.cia,
        'ign': None,
    }))
    assert resp.json['collection'][2] == json.loads(dumps({
        'attributes': None,
        'laposte': None,
        'ordinal': 'bis',
        'parent': street.id,
        'id': hn3.id,
        'version': 1,
        'postcode': None,
        'number': '3',
        'resource': 'housenumber',
        'cia': hn3.cia,
        'ign': None,
    }))


@authorize
def test_create_group(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "900010234",
        "municipality": municipality.id,
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['name'] == 'Rue de la Plage'
    assert resp.json['municipality'] == municipality.id
    assert models.Group.select().count() == 1
    uri = 'http://localhost/group/{}'.format(resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize
def test_cannot_create_group_without_kind(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "900010234",
        "municipality": municipality.id,
    }
    resp = client.post('/group', data)
    assert resp.status_code == 422


@authorize
def test_create_group_with_municipality_insee(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "900010234",
        "municipality": "insee:{}".format(municipality.insee),
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status_code == 201
    assert models.Group.select().count() == 1
    uri = 'http://localhost/group/{}'.format(resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize
def test_create_group_with_municipality_siren(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "900010234",
        "municipality": "siren:{}".format(municipality.siren),
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status_code == 201
    assert models.Group.select().count() == 1


@authorize
def test_create_group_with_bad_municipality_siren(client):
    MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "900010234",
        "municipality": "siren:{}".format('bad'),
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status_code == 422
    assert not models.Group.select().count()


@authorize
def test_create_group_with_invalid_municipality_identifier(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "900010234",
        "municipality": "invalid:{}".format(municipality.insee),
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status_code == 422
    assert not models.Group.select().count()


@authorize
def test_get_group_versions(get):
    street = GroupFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    resp = get('/group/{}/versions'.format(street.id))
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 2
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['data']['name'] == 'Rue de la Paix'
    assert resp.json['collection'][1]['data']['name'] == 'Rue de la Guerre'


@authorize
def test_get_group_version(get):
    street = GroupFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    uri = '/group/{}/versions/{}'.format(street.id, 1)
    resp = get(uri)
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Rue de la Paix'
    assert resp.json['data']['version'] == 1
    uri = '/group/{}/versions/{}'.format(street.id, 2)
    resp = get(uri)
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Rue de la Guerre'
    assert resp.json['data']['version'] == 2


@authorize
def test_get_group_unknown_version_should_go_in_404(get):
    street = GroupFactory(name="Rue de la Paix")
    resp = get('/group/{}/versions/{}'.format(street.id, 2))
    assert resp.status_code == 404


@authorize
def test_delete_street(client):
    street = GroupFactory()
    resp = client.delete('/group/{}'.format(street.id))
    assert resp.status_code == 200
    assert resp.json['resource_id'] == street.id
    assert not models.Group.select().count()


def test_cannot_delete_group_if_not_authorized(client):
    street = GroupFactory()
    resp = client.delete('/group/{}'.format(street.id))
    assert resp.status_code == 401
    assert models.Group.get(models.Group.id == street.id)


@authorize
def test_cannot_delete_group_if_linked_to_housenumber(client):
    street = GroupFactory()
    HouseNumberFactory(parent=street)
    resp = client.delete('/group/{}'.format(street.id))
    assert resp.status_code == 409
    assert models.Group.get(models.Group.id == street.id)


@authorize
def test_create_district_with_json_string_as_attribute(client):
    assert not models.Group.select().count()
    municipality = MunicipalityFactory()
    data = {
        "name": "Lhomme",
        "attributes": json.dumps({"key": "value"}),
        "municipality": municipality.id,
        "kind": models.Group.AREA,
    }
    resp = client.post('/group', data)
    assert resp.status_code == 201
    assert resp.json['attributes'] == {"key": "value"}


@authorize
def test_group_select_use_default_orderby(get):
    GroupFactory(insee="90001", fantoir="900010002")
    GroupFactory(insee="90001", fantoir="900010001")
    resp = get('/group')
    assert resp.status_code == 200
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['fantoir'] == '900010002'
    assert resp.json['collection'][1]['fantoir'] == '900010001'
