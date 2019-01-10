from ban.core import models

from ..factories import PostCodeFactory, MunicipalityFactory
from .utils import authorize


@authorize
def test_get_postcode(get):
    postcode = PostCodeFactory(code="09350", name="EPINAY SUR SEINE")
    resp = get('/postcode/{}'.format(postcode.id))
    assert resp.status_code == 200
    assert resp.json == {
        'id': postcode.id,
        'name': 'EPINAY SUR SEINE',
        'code': '09350',
        'alias': [],
        'modified_at': postcode.modified_at.isoformat(),
        'created_at': postcode.created_at.isoformat(),
        'modified_by': postcode.modified_by.serialize(),
        'created_by': postcode.created_by.serialize(),
        'attributes': None,
        'status': 'active',
        'version': 1,
        'complement': None,
        'municipality': postcode.municipality.id,
    }


@authorize
def test_get_postcode_name_search(get):
    postcode = PostCodeFactory(code="13800", name="ISTRES")
    resp = get('/postcode?searchName=ISTRES')
    assert resp.status_code == 200
    assert resp.json['collection'][0]['name'] == "ISTRES"


@authorize('postcode_write')
def test_create_postcode(client):
    municipality = MunicipalityFactory()
    assert not models.PostCode.select().count()
    data = {
        "code": "09350",
        "name": "Fornex",
        "municipality": municipality.id,
        "alias": ['Fornex_alias']
    }
    resp = client.post('/postcode', data)
    assert resp.status_code == 201
    assert resp.json['id']
    assert resp.json['code'] == '09350'
    assert resp.json['name'] == 'Fornex'
    assert resp.json['alias'] == ['Fornex_alias']
    assert models.PostCode.select().count() == 1
    uri = 'http://localhost/postcode/{}'.format(resp.json['id'])
    assert resp.headers['Location'] == uri


@authorize('postcode_write')
def test_can_update_postcode_complement(client):
    postcode = PostCodeFactory()
    data = {
        "complement": "SAINT SAINT",
        "version": 2
    }
    resp = client.post('/postcode/{}'.format(postcode.id), data)
    assert resp.status_code == 200
    assert resp.json['complement'] == "SAINT SAINT"


@authorize('postcode_write')
def test_can_create_postcode_with_same_code_but_different_complement(client):
    assert not models.PostCode.select().count()
    postcode = PostCodeFactory(code='12345', name='VILLE',
                               complement="QUARTIER")
    data = {
        "code": "12345",
        "name": "VILLE",
        "complement": "AUTRE QUARTIER",
        "municipality": postcode.municipality.id,
    }
    resp = client.post('/postcode', data)
    assert resp.status_code == 201
    assert models.PostCode.select().count() == 2


@authorize('postcode_write')
def test_cannot_duplicate_code_complement_and_municipality(client):
    assert not models.PostCode.select().count()
    postcode = PostCodeFactory(code='12345', name='VILLE',
                               complement="QUARTIER")
    data = {
        "code": "12345",
        "name": "VILLE",
        "complement": "QUARTIER",
        "municipality": postcode.municipality.id,
    }
    resp = client.post('/postcode', data)
    assert resp.status_code == 422
    assert models.PostCode.select().count() == 1
    assert 'code' in resp.json['errors']
    assert 'complement' in resp.json['errors']
    assert 'municipality' in resp.json['errors']


@authorize('postcode_write')
def test_postcode_select_use_default_orderby(get):
    mun1 = MunicipalityFactory(insee="90002")
    mun2 = MunicipalityFactory(insee="90001")
    PostCodeFactory(code="90102", municipality=mun1)
    PostCodeFactory(code="90102", municipality=mun2)
    PostCodeFactory(code="90101", municipality=mun2)
    resp = get('/postcode')
    assert resp.status_code == 200
    assert resp.json['total'] == 3
    assert resp.json['collection'][0]['code'] == '90101'
    assert resp.json['collection'][1]['municipality'] == mun1.id
    assert resp.json['collection'][2]['municipality'] == mun2.id


@authorize
def test_get_postcode_collection_filtered_by_1_code_param(get):
    PostCodeFactory(code='90000')
    PostCodeFactory(code='91000')
    resp = get('/postcode?code=90000')
    assert resp.status_code == 200
    assert resp.json['total'] == 1
    assert resp.json['collection'][0]['code'] == '90000'


@authorize
def test_get_postcode_collection_filtered_by_2_equals_codes_param(get):
    PostCodeFactory(code='90000')
    PostCodeFactory(code='91000')
    # 'code' given by the user is used twice but with the same value.
    resp = get('/postcode?code=90000&code=90000')
    assert resp.status_code == 200
    assert resp.json['total'] == 1
    assert resp.json['collection'][0]['code'] == '90000'


@authorize
def test_get_postcode_collection_filtered_by_2_diff_codes_param(get):
    PostCodeFactory(code='90000')
    PostCodeFactory(code='91000')
    # 'code' given by the user is used with 2 differents values.
    resp = get('/postcode?code=90000&code=91000')
    assert resp.status_code == 200
    assert resp.json['total'] == 2
    assert resp.json['collection'][0]['code'] == '90000'
    assert resp.json['collection'][1]['code'] == '91000'


@authorize
def test_get_postcode_collection_can_be_filtered_by_1_code_and_1_pk(get):
    PostCodeFactory(code='90000')
    PostCodeFactory(code='91000')
    # Only 'Code' param will be used to filter, not 'pk' one.
    resp = get('/postcode?code=90000&pk=405')
    assert resp.status_code == 200
    assert resp.json['total'] == 1
    assert resp.json['collection'][0]['code'] == '90000'
