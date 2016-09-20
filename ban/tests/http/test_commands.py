from io import BytesIO

from ban.core import models
from ban.tests import factories

from .utils import authorize


@authorize
def test_bal_import_from_data_file(staff, client):
    factories.MunicipalityFactory(name="Acigné", insee="35001")
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0005_99999,,Mail Anita Conti,99999,,Acigné,,,,,,Rennes Métropole,2016-02-22
"""
    resp = client.post('/import/bal',
                       data={'data': (BytesIO(content.encode()), 'test.csv')},
                       content_type='multipart/form-data')
    assert resp.status_code == 200
    assert models.Group.select().count() == 1
    group = models.Group.select().first()
    assert group.name == "Mail Anita Conti"
    assert group.fantoir == "350010005"
    assert 'report' in resp.json
    assert 'notice' in resp.json['report']


def test_cannot_use_bal_import_without_auth(staff, client):
    factories.MunicipalityFactory(name="Acigné", insee="35001")
    resp = client.post('/import/bal', data={'data': (b'xxxx', 'test.csv')},
                       content_type='multipart/form-data')
    assert resp.status_code == 401


@authorize
def test_data_file_is_mandatory(staff, client):
    resp = client.post('/import/bal', data={'badname': (b'aaa', 'test.csv')},
                       content_type='multipart/form-data')
    assert resp.status_code == 400
