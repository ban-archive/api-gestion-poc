import pytest

import falcon
from ban import http


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
