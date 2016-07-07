import falcon
from ban.core import models

from ..factories import PostCodeFactory, MunicipalityFactory
from .utils import authorize


@authorize
def test_get_postcode(get, url):
    postcode = PostCodeFactory(code="09350")
    resp = get(url('postcode-resource', identifier=postcode.id))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['code'] == '09350'


@authorize
def test_create_postcode(client, url):
    municipality = MunicipalityFactory()
    assert not models.PostCode.select().count()
    data = {
        "code": "09350",
        "name": "Fornex",
        "municipality": municipality.id
    }
    resp = client.post(url('postcode'), data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['code'] == '09350'
    assert models.PostCode.select().count() == 1
    uri = "https://falconframework.org{}".format(url('postcode-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_postcode_select_use_default_orderby(get, url):
    mun1 = MunicipalityFactory(insee="90002")
    mun2 = MunicipalityFactory(insee="90001")
    PostCodeFactory(code="90102", municipality=mun1)
    PostCodeFactory(code="90102", municipality=mun2)
    PostCodeFactory(code="90101", municipality=mun2)
    uri = url('postcode')
    resp = get(uri)
    assert resp.status == falcon.HTTP_200
    assert resp.json['total'] == 3
    assert resp.json['collection'][0]['code'] == '90101'
    assert resp.json['collection'][1]['municipality']['insee'] == "90002"
    assert resp.json['collection'][2]['municipality']['insee'] == "90001"
