import json

import falcon
from ban.core import models

from ..factories import DistrictFactory, MunicipalityFactory
from .utils import authorize


def test_get_district(get, url):
    district = DistrictFactory(name="Lhomme")
    resp = get(url('district-resource', identifier=district.id))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['name'] == 'Lhomme'
    assert resp.json['municipality']['id'] == district.municipality.id


@authorize
def test_create_district(client, url):
    assert not models.District.select().count()
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
    assert models.District.select().count() == 1
    uri = "https://falconframework.org{}".format(url('district-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_create_district_with_json_string_as_attribute(client, url):
    assert not models.District.select().count()
    municipality = MunicipalityFactory()
    data = {
        "name": "Lhomme",
        "attributes": json.dumps({"key": "value"}),
        "municipality": municipality.id
    }
    resp = client.post(url('district'), data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['attributes'] == {"key": "value"}
