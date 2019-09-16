import json

from ban.core import models
from ban.core.encoder import dumps

from ..factories import HouseNumberFactory, MunicipalityFactory, GroupFactory, PositionFactory
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
    assert len(resp.json['collection']) == 3
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
def test_get_group_name_search_invalid_type(get):
    street = GroupFactory(name="Rue des Boulets")
    resp = get('/group?searchName=Rue+des+Boulets&searchType=wrong')
    assert resp.status_code == 400


@authorize
def test_get_group_name_search_case_sensitive(get):
    street = GroupFactory(name="Rue des Boulets")
    resp = get('/group?searchName=Rue+des+Boulets')
    assert resp.status_code == 200
    assert resp.json['collection'][0]['name'] == "Rue des Boulets"


@authorize
def test_get_group_name_search_case_insensitive(get):
    street = GroupFactory(name="Rue des Boulets")
    resp = get('/group?searchName=RUE+DES+BOULETS&searchType=case')
    assert resp.status_code == 200
    assert resp.json['collection'][0]['name'] == "Rue des Boulets"

@authorize
def test_get_group_name_search_case_insensitive_accent(get):
    street = GroupFactory(name="Rue de la boulangère")
    resp = get('/group?searchName=RUE+DE+LA+BOULANGERE&searchType=case')
    assert resp.status_code == 200
    assert resp.json['collection'][0]['name'] == "Rue de la boulangère"

@authorize('group_write')
def test_create_group(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "   Rue de   la Plage",
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


@authorize('group_write')
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


@authorize('group_write')
def test_cannot_create_group_whitespace_name(client):
    municipality = MunicipalityFactory(name="Cabour")
    assert not models.Group.select().count()
    data = {
        "name": "   ",
        "kind": "area",
        "fantoir": "900010234",
        "municipality": municipality.id
    }
    resp = client.post('/group', data)
    assert resp.status_code == 422


@authorize('group_write')
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


@authorize('group_write')
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


@authorize('group_write')
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


@authorize('group_write')
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


@authorize('group_write')
def test_create_group_on_deleted_municipality(client):
    municipality = MunicipalityFactory()
    municipality.mark_deleted()
    assert not models.Group.select().count()
    data = {
        "name": "Rue de la Plage",
        "fantoir": "900010234",
        "municipality": municipality.id,
        "kind": models.Group.WAY,
    }
    resp = client.post('/group', data)
    assert resp.status_code == 422
    assert not models.Group.select().count()
    assert resp.json['errors']['municipality'] == (
        'Resource `municipality` with id `{}` is deleted'.format(municipality.id))


@authorize('group_write')
def test_get_group_versions(get):
    street = GroupFactory(name="Rue de la Paix")
    street.version = 2
    street.name = "Rue de la Guerre"
    street.save()
    resp = get('/group/{}/versions'.format(street.id))
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 2
    assert resp.json['collection'][0]['data']['name'] == 'Rue de la Paix'
    assert resp.json['collection'][1]['data']['name'] == 'Rue de la Guerre'


@authorize('group_write')
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


@authorize('group_write')
def test_get_group_unknown_version_should_go_in_404(get):
    street = GroupFactory(name="Rue de la Paix")
    resp = get('/group/{}/versions/{}'.format(street.id, 2))
    assert resp.status_code == 404


@authorize('group_write')
def test_delete_street(client):
    street = GroupFactory()
    resp = client.delete('/group/{}'.format(street.id))
    assert resp.status_code == 204
    assert models.Group.select().count() == 1
    assert models.Group.raw_select().where(
                                models.Group.pk == street.pk).get().deleted_at


def test_cannot_delete_group_if_not_authorized(client):
    street = GroupFactory()
    resp = client.delete('/group/{}'.format(street.id))
    assert resp.status_code == 401
    assert models.Group.get(models.Group.id == street.id)


@authorize('group_foo')
def test_cannot_delete_group_without_correct_scope(client):
    street = GroupFactory()
    resp = client.delete('/group/{}'.format(street.id))
    assert resp.status_code == 401
    assert models.Group.get(models.Group.id == street.id)


@authorize('group_write')
def test_cannot_delete_group_if_linked_to_housenumber(client):
    street = GroupFactory()
    HouseNumberFactory(parent=street)
    resp = client.delete('/group/{}'.format(street.id))
    assert resp.status_code == 409
    assert models.Group.get(models.Group.id == street.id)


@authorize('group_write')
def test_create_group_with_json_string_as_attribute(client):
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
    assert len(resp.json['collection']) == 2
    assert resp.json['collection'][0]['fantoir'] == '900010002'
    assert resp.json['collection'][1]['fantoir'] == '900010001'


@authorize('group_write')
def test_group_merge_ok(client):
    street = GroupFactory()
    erased_street = GroupFactory()
    master_ancestor = GroupFactory()
    erased_ancestor = GroupFactory()
    hn_master = HouseNumberFactory(number=4, parent=street, ancestors=[master_ancestor])
    hn_erased = HouseNumberFactory(number=4, parent=erased_street, ancestors=[erased_ancestor])
    oth_hn_erased = HouseNumberFactory(number=5, parent=erased_street)
    pos_master = PositionFactory(center=(1,1), kind="entrance", housenumber=hn_master)
    pos_erased = PositionFactory(center=(2,2), kind="entrance", housenumber=hn_erased)
    pos_erased_oth = PositionFactory(center=(3,3), kind="parcel", housenumber=hn_erased)

    data = {
        "erased_group_id": erased_street.id,
        "master_group_version": (street.version + 1),
        "prior_position": "erased"
    }
    resp = client.post('/group/merge/{}'.format(street.id), data)
    assert resp.status_code == 200
    assert resp.json['id'] == street.id
    assert list(street.housenumbers) == [hn_master, oth_hn_erased]
    assert list(hn_master.ancestors) == [master_ancestor, erased_ancestor]
    assert models.Position.raw_select().where(
        models.Position.pk == pos_master.pk).get().deleted_at
    assert models.Position.raw_select().where(
        models.Position.pk == pos_erased.pk).get().housenumber == hn_master


@authorize('group_write')
def test_group_merge_invalid_data(client):
    street = GroupFactory()
    erased_street = GroupFactory()
    resp = client.post('/group/merge/{}'.format(street.id), {"erased_group_id": street.id, "prior_position": "plop"})
    assert resp.status_code == 422
    assert "prior_position" in resp.json["errors"].keys()
    assert "master_group_version" in resp.json["errors"].keys()


@authorize('group_write')
def test_group_merge_master_not_found(client):
    street = GroupFactory()
    erased_street = GroupFactory()
    resp = client.post(
        '/group/merge/{}'.format("plop"),
        {"erased_group_id": erased_street.id, "prior_position": "master", "master_group_version": 2}
    )
    assert resp.status_code == 404


@authorize('group_write')
def test_group_merge_wrong_version(client):
    street = GroupFactory()
    erased_street = GroupFactory()
    resp = client.post(
        '/group/merge/{}'.format(street.id),
        {"erased_group_id": erased_street.id, "prior_position": "master", "master_group_version": 4}
    )
    assert resp.status_code == 409


@authorize('group_write')
def test_group_merge_erased_deleted(client):
    street = GroupFactory()
    erased_street = GroupFactory()
    erased_street.mark_deleted()
    resp = client.post(
        '/group/merge/{}'.format(street.id),
        {"erased_group_id": erased_street.id, "prior_position": "master", "master_group_version": 2}
    )
    assert resp.status_code == 410
