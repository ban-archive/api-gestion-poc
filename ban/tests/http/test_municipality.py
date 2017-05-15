import json
from datetime import datetime

from ban.core import models, context
from ban.core.encoder import dumps
from ban.core.versioning import Version, Redirect
from ban.utils import utcnow

from ..factories import MunicipalityFactory, PostCodeFactory, GroupFactory
from .utils import authorize


@authorize
def test_get_municipality(get):
    municipality = MunicipalityFactory(name="Cabour")
    resp = get('/municipality/{}'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


@authorize
def test_get_municipality_with_postcodes(get):
    municipality = MunicipalityFactory(name="Cabour")
    postcode = PostCodeFactory(code="33000", municipality=municipality)
    resp = get('/municipality/{}'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'
    assert resp.json['postcodes'] == [postcode.id]


@authorize
def test_get_municipality_without_explicit_identifier(get):
    municipality = MunicipalityFactory(name="Cabour")
    resp = get('/municipality/{}'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


@authorize
def test_get_municipality_groups_collection(get):
    municipality = MunicipalityFactory(name="Cabour")
    street = GroupFactory(municipality=municipality, name="Rue de la Plage")
    resp = get('/group?municipality={}'.format(municipality.id))
    assert resp.status_code == 200
    # loads/dumps to compare date strings to date strings.
    assert resp.json['collection'][0] == json.loads(dumps(street.as_relation))
    assert resp.json['total'] == 1


@authorize
def test_get_municipality_groups_collection_is_paginated(get):
    municipality = MunicipalityFactory(name="Cabour")
    GroupFactory.create_batch(6, municipality=municipality)
    resp = get('/group?municipality={}&limit=4'.format(municipality.id))
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


@authorize
def test_get_municipality_collection_is_ceiled(get, monkeypatch):
    monkeypatch.setattr('ban.http.api.CollectionEndpoint.MAX_LIMIT', 4)
    MunicipalityFactory.create_batch(6)
    resp = get('/municipality?limit=6')
    page1 = resp.json
    assert len(page1['collection']) == 4
    assert page1['total'] == 6


@authorize
def test_get_municipality_versions(get):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    resp = get('/municipality/{}/versions'.format(municipality.id))
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 2
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['data']['name'] == 'Cabour'
    assert resp.json['collection'][1]['data']['name'] == 'Cabour2'


@authorize
def test_get_municipality_versions_by_datetime(get):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    # Artificialy change versions periods.
    period = [datetime(2015, 1, 1), datetime(2016, 1, 1)]
    Version.update(period=period).where(Version.sequential == 1).execute()
    period = [datetime(2016, 1, 1), None]
    Version.update(period=period).where(Version.sequential == 2).execute()
    # Should work with a simple datetime.
    resp = get('/municipality/{}/versions/2015-06-01T01:02:03+00:00'
               .format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour'
    # Should work with a naive datetime too.
    resp = get('/municipality/{}/versions/2015-06-01 01:02:03'
               .format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour'
    # Should work with a simple date too.
    resp = get('/municipality/{}/versions/2015-06-01'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour'
    # Now ask in the range of the second version
    resp = get('/municipality/{}/versions/2016-06-01'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour2'
    # Asking for the common bound should return the new version.
    resp = get('/municipality/{}/versions/2016-01-01 00:00:00'
               .format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour2'


@authorize
def test_get_versions_by_datetime_should_raise_if_format_is_invalid(get):
    municipality = MunicipalityFactory(name="Cabour")
    # Artificialy change versions periods.
    resp = get('/municipality/{}/versions/01:02:032015-06-01'
               .format(municipality.id))
    assert resp.status_code == 404


@authorize
def test_get_municipality_version(get):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    resp = get('/municipality/{}/versions/1'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour'
    assert resp.json['data']['version'] == 1
    resp = get('/municipality/{}/versions/2'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour2'
    assert resp.json['data']['version'] == 2


@authorize
def test_old_insee_should_redirect(get):
    municipality = MunicipalityFactory(insee="12345")
    # This should create a redirect.
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    # Request with old insee.
    resp = get('/municipality/insee:12345')
    assert resp.status_code == 302
    assert resp.headers['Location'] == 'http://localhost/municipality/{}'.format(municipality.id)  # noqa


@authorize
def test_multiple_redirects_should_return_300(get):
    municipality1 = MunicipalityFactory(insee="23456")
    municipality2 = MunicipalityFactory(insee="34567")
    # Let's say this municipality has been split.
    Redirect.add(municipality1, 'insee', '12345')
    Redirect.add(municipality2, 'insee', '12345')
    resp = get('/municipality/insee:12345')
    assert resp.status_code == 300
    assert '/municipality/{}'.format(municipality1.id) in resp.headers['Link']
    assert '/municipality/{}'.format(municipality1.id) in resp.json['choices']
    assert '/municipality/{}'.format(municipality2.id) in resp.headers['Link']
    assert '/municipality/{}'.format(municipality2.id) in resp.json['choices']


@authorize
def test_create_municipality(post):
    assert not models.Municipality.select().count()
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
    }
    resp = post('/municipality', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['name'] == 'Fornex'
    assert models.Municipality.select().count() == 1
    uri = 'http://localhost/municipality/{}'.format(resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize
def test_cannot_duplicate_municipality(post):
    MunicipalityFactory(insee="12345")
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
    }
    resp = post('/municipality', data)
    assert resp.status_code == 422
    assert 'errors' in resp.json
    assert resp.json['errors']['insee']
    assert '12345' in resp.json['errors']['insee']


@authorize
def test_create_municipality_with_one_alias(post):
    data = {
        "name": "Orvane",
        "insee": "12345",
        "siren": '123456789',
        "alias": 'Moret-sur-Loing'
    }
    resp = post('/municipality', data)
    assert resp.status_code == 201
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias


@authorize
def test_create_municipality_with_list_of_aliases(post):
    data = {
        "name": "Orvane",
        "insee": "12345",
        "siren": '123456789',
        "alias": ['Moret-sur-Loing', 'Another-Name']
    }
    resp = post('/municipality', data)
    assert resp.status_code == 201
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias
    assert 'Another-Name' in municipality.alias


@authorize
def test_patch_municipality_with_alias(patch):
    municipality = MunicipalityFactory()
    data = {
        "version": 2,
        "alias": ['Moret-sur-Loing']
    }
    resp = patch('/municipality/{}'.format(municipality.id), data)
    assert resp.status_code == 200
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias


@authorize
def test_delete_municipality(client):
    municipality = MunicipalityFactory()
    resp = client.delete('/municipality/{}'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['resource_id'] == municipality.id
    assert not models.Municipality.select().count()
    assert models.Municipality.raw_select().where(
                models.Municipality.pk == municipality.pk).first().deleted_at


def test_cannot_delete_municipality_if_not_authorized(client):
    municipality = MunicipalityFactory()
    resp = client.delete('/municipality/{}'.format(municipality.id))
    assert resp.status_code == 401
    assert models.Municipality.get(models.Municipality.id == municipality.id)


@authorize
def test_cannot_delete_municipality_if_linked_to_street(client):
    municipality = MunicipalityFactory()
    GroupFactory(municipality=municipality)
    resp = client.delete('/municipality/{}'.format(municipality.id))
    assert resp.status_code == 409
    assert resp.json['error'] == 'Resource still linked by `groups`'
    assert models.Municipality.get(models.Municipality.id == municipality.id)


@authorize
def test_delete_unknown_municipality_should_return_not_found(client):
    resp = client.delete('/municipality/11')
    assert resp.status_code == 404


@authorize
def test_can_get_deleted_municipality(get):
    municipality = MunicipalityFactory()
    municipality.mark_deleted()
    resp = get('/municipality/{}'.format(municipality.id))
    assert resp.status_code == 410
    assert resp.json['id'] == municipality.id
    assert len(municipality.versions) == 2


@authorize
def test_can_get_deleted_municipality_versions(get):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    resp = get('/municipality/{}/versions'.format(municipality.id))
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 2
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['data']['name'] == 'Cabour'
    assert resp.json['collection'][1]['data']['name'] == 'Cabour2'


@authorize
def test_can_get_deleted_municipality_version(get):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    resp = get('/municipality/{}/versions/2'.format(municipality.id))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour2'


@authorize
def test_cannot_post_on_deleted_municipality(post):
    municipality = MunicipalityFactory()
    municipality.mark_deleted()
    resp = post('/municipality/{}'.format(municipality.id), data={})
    assert resp.status_code == 410


@authorize
def test_cannot_patch_on_deleted_municipality(patch):
    municipality = MunicipalityFactory()
    municipality.mark_deleted()
    resp = patch('/municipality/{}'.format(municipality.id), data={})
    assert resp.status_code == 410


@authorize
def test_can_restore_municipality(client):
    municipality = MunicipalityFactory()
    municipality.mark_deleted()
    data = municipality.serialize({'*': {}})
    data['version'] = 3
    resp = client.put('/municipality/{}'.format(municipality.id), data=data)
    assert resp.status_code == 200
    assert not models.Municipality.get(
        models.Municipality.pk == municipality.pk).deleted_at
    assert len(municipality.versions) == 3


@authorize
def test_cannot_restore_municipality_without_changing_version(client):
    municipality = MunicipalityFactory()
    municipality.mark_deleted()
    data = municipality.serialize({'*': {}})
    resp = client.put('/municipality/{}'.format(municipality.id), data=data)
    assert resp.status_code == 409
    assert models.Municipality.raw_select().where(
        models.Municipality.pk == municipality.pk).get().deleted_at


@authorize
def test_cannot_restore_municipality_with_invalid_data(client):
    municipality = MunicipalityFactory()
    municipality.mark_deleted()
    data = municipality.serialize({'*': {}})
    data['name'] = ''
    data['version'] = 3
    resp = client.put('/municipality/{}'.format(municipality.id), data=data)
    assert resp.status_code == 422
    assert models.Municipality.raw_select().where(
        models.Municipality.pk == municipality.pk).get().deleted_at


@authorize
def test_municipality_select_use_default_orderby(get):
    MunicipalityFactory(insee="90002")
    MunicipalityFactory(insee="90001")
    resp = get('/municipality')
    assert resp.status_code == 200
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['insee'] == '90001'


@authorize
def test_status_is_readonly(post):
    municipality = MunicipalityFactory()
    data = municipality.serialize({'*': {}})
    data['status'] = 'deleted'
    data['version'] = 2
    resp = post('/municipality/{}'.format(municipality.id), data=data)
    assert resp.status_code == 200


@authorize
def test_cannot_change_deleted_at_with_post(post):
    municipality = MunicipalityFactory()
    data = municipality.serialize({'*': {}})
    data['deleted_at'] = utcnow().isoformat()
    data['version'] = 2
    resp = post('/municipality/{}'.format(municipality.id), data=data)
    assert resp.status_code == 200
    assert not models.Municipality.get(
        models.Municipality.pk == municipality.pk).deleted_at


@authorize
def test_cannot_change_deleted_at_with_patch(patch):
    municipality = MunicipalityFactory()
    data = municipality.serialize({'*': {}})
    data['deleted_at'] = utcnow().isoformat()
    data['version'] = 2
    resp = patch('/municipality/{}'.format(municipality.id), data=data)
    assert resp.status_code == 200
    assert not models.Municipality.get(
        models.Municipality.pk == municipality.pk).deleted_at


@authorize
def test_cannot_change_deleted_at_with_put(put):
    municipality = MunicipalityFactory()
    data = municipality.serialize({'*': {}})
    data['deleted_at'] = utcnow().isoformat()
    data['version'] = 2
    resp = put('/municipality/{}'.format(municipality.id), data=data)
    assert resp.status_code == 200
    assert not models.Municipality.get(
        models.Municipality.pk == municipality.pk).deleted_at


@authorize
def test_authorized_responses_contain_sessions_data(get):
    municipality = MunicipalityFactory(name="Cabour")
    resp = get('/municipality/{}'.format(municipality.id))
    assert resp.status_code == 200
    session = context.get('session')
    assert resp.headers['Session-Client'] == session.client.id
    assert resp.headers['Session-User'] == session.user.id
