from ban.core import models

from ..factories import PostCodeFactory, MunicipalityFactory
from .utils import authorize


@authorize
def test_get_postcode(get, url):
    postcode = PostCodeFactory(code="09350")
    resp = get(url('postcode-resource', identifier=postcode.id))
    assert resp.status_code == 200
    assert resp.json['id']
    assert resp.json['code'] == '09350'


@authorize
def test_create_postcode(client, url):
    municipality = MunicipalityFactory()
    assert not models.PostCode.select().count()
    data = {
        "code": "09350",
        "name": "Fornex",
        "municipality": municipality.id,
        "alias": ['Fornex_alias']
    }
    resp = client.post(url('postcode-post'), data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['code'] == '09350'
    assert resp.json['name'] == 'Fornex'
    assert resp.json['alias'] == ['Fornex_alias']
    assert models.PostCode.select().count() == 1
    uri = url('postcode-resource', identifier=resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize
def test_postcode_select_use_default_orderby(get, url):
    mun1 = MunicipalityFactory(insee="90002")
    mun2 = MunicipalityFactory(insee="90001")
    PostCodeFactory(code="90102", municipality=mun1)
    PostCodeFactory(code="90102", municipality=mun2)
    PostCodeFactory(code="90101", municipality=mun2)
    resp = get(url('post_code_collection'))
    assert resp.status_code == 200
    assert resp.json['total'] == 3
    assert resp.json['collection'][0]['code'] == '90101'
    assert resp.json['collection'][1]['municipality'] == mun1.id
    assert resp.json['collection'][2]['municipality'] == mun2.id


@authorize
def test_get_postcode_collection_filtered_by_1_code_param(get, url):
    PostCodeFactory(code='90000')
    PostCodeFactory(code='91000')
    resp = get(url('post_code_collection', code='90000'))
    assert resp.status_code == 200
    assert resp.json['total'] == 1
    assert resp.json['collection'][0]['code'] == '90000'


@authorize
def test_get_postcode_collection_filtered_by_2_equals_codes_param(get, url):
    PostCodeFactory(code='90000')
    PostCodeFactory(code='91000')
    # 'code' given by the user is used twice but with the same value.
    resp = get(url('post_code_collection', code=['90000', '90000']))
    assert resp.status_code == 200
    assert resp.json['total'] == 1
    assert resp.json['collection'][0]['code'] == '90000'


@authorize
def test_get_postcode_collection_filtered_by_2_diff_codes_param(get, url):
    PostCodeFactory(code='90000')
    PostCodeFactory(code='91000')
    # 'code' given by the user is used with 2 differents values.
    resp = get(url('post_code_collection', code=['90000', '91000']))
    assert resp.status_code == 200
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['code'] == '90000'
    assert resp.json['collection'][1]['code'] == '91000'


@authorize
def test_get_postcode_collection_can_be_filtered_by_1_code_and_1_pk(get, url):
    PostCodeFactory(code='90000')
    PostCodeFactory(code='91000')
    # Only 'Code' param will be used to filter, not 'pk' one.
    params = {'code': '90000', 'pk': '405'}
    resp = get(url('post_code_collection', **params))
    assert resp.status_code == 200
    assert resp.json['total'] == 1
    assert resp.json['collection'][0]['code'] == '90000'
