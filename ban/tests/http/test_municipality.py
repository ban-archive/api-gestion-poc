import json
from datetime import datetime

from ban.core import models
from ban.core.encoder import dumps
from ban.core.versioning import Version
from ban.http import api

from ..factories import MunicipalityFactory, PostCodeFactory, GroupFactory
from .utils import authorize


@authorize
def test_get_municipality(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    uri = url(api.Municipality, identifier=municipality.id)
    resp = get(uri)
    assert resp.status_code == 200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


@authorize
def test_get_municipality_with_postcodes(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    postcode = PostCodeFactory(code="33000", municipality=municipality)
    uri = url(api.Municipality, identifier=municipality.id)
    resp = get(uri)
    assert resp.status_code == 200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'
    assert resp.json['postcodes'] == [{
        'id': postcode.id,
        'attributes': None,
        'code': '33000',
        'name': 'Test PostCode Area Name',
        'municipality': municipality.id,
        'resource': 'postcode',
        'alias': None,
        'version': 1,
    }]


@authorize
def test_get_municipality_without_explicit_identifier(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    uri = url(api.Municipality, identifier=municipality.id)
    resp = get(uri)
    assert resp.status_code == 200
    assert resp.json['id']
    assert resp.json['name'] == 'Cabour'


@authorize
def test_get_municipality_groups_collection(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    street = GroupFactory(municipality=municipality, name="Rue de la Plage")
    uri = url(api.GroupCollection, municipality=municipality.id)
    resp = get(uri)
    assert resp.status_code == 200
    # loads/dumps to compare date strings to date strings.
    assert resp.json['collection'][0] == json.loads(dumps(street.as_relation))
    assert resp.json['total'] == 1


@authorize
def test_get_municipality_groups_collection_is_paginated(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    GroupFactory.create_batch(6, municipality=municipality)
    uri = url(api.GroupCollection, identifier=municipality.id, limit=4)
    resp = get(uri)
    page1 = resp.json
    assert len(page1['collection']) == 4
    assert page1['total'] == 6
    assert 'next' in page1
    assert 'previous' not in page1
    # assert page1['next'] in resp.headers['Link']
    resp = get(page1['next'])
    page2 = resp.json
    assert len(page2['collection']) == 2
    assert page2['total'] == 6
    assert 'next' not in page2
    assert 'previous' in page2
    # assert page2['previous'] in resp.headers['Link']
    resp = get(page2['previous'])
    assert resp.json == page1


@authorize
def test_get_municipality_versions(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    uri = url(api.MunicipalityVersionCollection, identifier=municipality.id)
    resp = get(uri)
    assert resp.status_code == 200
    assert len(resp.json['collection']) == 2
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['data']['name'] == 'Cabour'
    assert resp.json['collection'][1]['data']['name'] == 'Cabour2'


@authorize
def test_get_municipality_versions_by_datetime(get, url):
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
    resp = get(url('municipality-version-by-date', identifier=municipality.id,
                   ref='2015-06-01T01:02:03+00:00'))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour'
    # Should work with a naive datetime too.
    resp = get(url('municipality-version-by-date', identifier=municipality.id,
                   ref='2015-06-01 01:02:03'))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour'
    # Should work with a simple date too.
    resp = get(url('municipality-version-by-date', identifier=municipality.id,
                   ref='2015-06-01'))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour'
    # Now ask in the range of the second version
    resp = get(url('municipality-version-by-date', identifier=municipality.id,
                   ref='2016-06-01'))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour2'
    # Asking for the common bound should return the new version.
    resp = get(url('municipality-version-by-date', identifier=municipality.id,
                   ref='2016-01-01 00:00:00'))
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour2'


@authorize
def test_get_versions_by_datetime_should_raise_if_format_is_invalid(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    # Artificialy change versions periods.
    resp = get(url('municipality-version-by-date', identifier=municipality.id,
                   ref='01:02:032015-06-01'))
    assert resp.status_code == 404


@authorize
def test_get_municipality_version(get, url):
    municipality = MunicipalityFactory(name="Cabour")
    municipality.version = 2
    municipality.name = "Cabour2"
    municipality.save()
    uri = url(api.MunicipalityVersion, identifier=municipality.id, ref=1)
    resp = get(uri)
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour'
    assert resp.json['data']['version'] == 1
    uri = url(api.MunicipalityVersion, identifier=municipality.id, ref=2)
    resp = get(uri)
    assert resp.status_code == 200
    assert resp.json['data']['name'] == 'Cabour2'
    assert resp.json['data']['version'] == 2


@authorize
def test_can_retrieve_municipality_with_old_insee(get, url):
    municipality = MunicipalityFactory(insee="12345")
    # This should create a redirect.
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    # Request with old insee.
    resp = get(url(api.Municipality, identifier='insee:12345'))
    assert resp.status_code == 200
    assert resp.json['id'] == municipality.id
    assert resp.json['insee'] == '54321'


@authorize
def test_create_municipality(post, url):
    assert not models.Municipality.select().count()
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
    }
    resp = post(url('municipality-post'), data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['name'] == 'Fornex'
    assert models.Municipality.select().count() == 1
    uri = url(api.Municipality, identifier=resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize
def test_cannot_duplicate_municipality(post, url):
    MunicipalityFactory(insee="12345")
    data = {
        "name": "Fornex",
        "insee": "12345",
        "siren": '123456789',
    }
    resp = post(url('municipality-post'), data)
    assert resp.status_code == 422
    assert resp.json['insee']
    assert '12345' in resp.json['insee']


@authorize
def test_create_municipality_with_one_alias(post, url):
    data = {
        "name": "Orvane",
        "insee": "12345",
        "siren": '123456789',
        "alias": 'Moret-sur-Loing'
    }
    resp = post(url('municipality-post'), data)
    assert resp.status_code == 201
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias


@authorize
def test_create_municipality_with_list_of_aliases(post, url):
    data = {
        "name": "Orvane",
        "insee": "12345",
        "siren": '123456789',
        "alias": ['Moret-sur-Loing', 'Another-Name']
    }
    resp = post(url('municipality-post'), data)
    assert resp.status_code == 201
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias
    assert 'Another-Name' in municipality.alias


@authorize
def test_patch_municipality_with_alias(patch, url):
    municipality = MunicipalityFactory()
    data = {
        "version": 2,
        "alias": ['Moret-sur-Loing']
    }
    uri = url(api.Municipality, identifier=municipality.id)
    resp = patch(uri, data)
    assert resp.status_code == 200
    municipality = models.Municipality.first()
    assert 'Moret-sur-Loing' in municipality.alias


@authorize
def test_delete_municipality(client, url):
    municipality = MunicipalityFactory()
    uri = url(api.Municipality, identifier=municipality.id)
    resp = client.delete(uri)
    assert resp.status_code == 200
    assert resp.json['resource_id'] == municipality.id
    assert not models.Municipality.select().count()


def test_cannot_delete_municipality_if_not_authorized(client, url):
    municipality = MunicipalityFactory()
    uri = url(api.Municipality, identifier=municipality.id)
    resp = client.delete(uri)
    assert resp.status_code == 401
    assert models.Municipality.get(models.Municipality.id == municipality.id)


@authorize
def test_cannot_delete_municipality_if_linked_to_street(client, url):
    municipality = MunicipalityFactory()
    GroupFactory(municipality=municipality)
    uri = url(api.Municipality, identifier=municipality.id)
    resp = client.delete(uri)
    assert resp.status_code == 409
    assert models.Municipality.get(models.Municipality.id == municipality.id)


@authorize
def test_delete_unknown_municipality_should_return_not_found(client, url):
    uri = url(api.Municipality, identifier=11)
    resp = client.delete(uri)
    assert resp.status_code == 404


@authorize
def test_municipality_select_use_default_orderby(get, url):
    MunicipalityFactory(insee="90002")
    MunicipalityFactory(insee="90001")
    resp = get(url('municipality-collection'))
    assert resp.status_code == 200
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['insee'] == '90001'
