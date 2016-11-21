import pytest

from ban.core import models
from ban.tests import factories
from ban.commands.municipality import merge
from ban.core import versioning


def test_unknown_destination_is_aborted():
    factories.MunicipalityFactory(insee='33001', name='Mun')
    with pytest.raises(SystemExit):
        merge('12345', sources=['33001'], name='Toto', label='TOTO')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1


def test_no_sources_is_aborted():
    factories.MunicipalityFactory(insee='33001', name='Mun')
    with pytest.raises(SystemExit):
        merge('33001')


def test_unknown_source_is_aborted():
    factories.MunicipalityFactory(insee='33001', name='Mun1')
    factories.MunicipalityFactory(insee='33002', name='Mun2')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002', '33333'], name='Toto', label='TOTO')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1


def test_destination_in_sources_is_aborted():
    factories.MunicipalityFactory(insee='33001', name='Mun1')
    factories.MunicipalityFactory(insee='33002', name='Mun2')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002', '33001'], name='Toto', label='TOTO')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1


def test_no_name_is_aborted():
    factories.MunicipalityFactory(insee='33001', name='Mun1')
    factories.MunicipalityFactory(insee='33002', name='Mun2')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002'], label='TOTO')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1


def test_no_label_is_aborted():
    factories.MunicipalityFactory(insee='33001', name='Mun1')
    factories.MunicipalityFactory(insee='33002', name='Mun2')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002'], name='Toto')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1


def test_redirect(session):
    mun1 = factories.MunicipalityFactory(insee='33001', name='Mun1')
    mun2 = factories.MunicipalityFactory(insee='33002', name='Mun2')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    assert versioning.Redirect.select().count() == 2
    assert versioning.Redirect.follow('Municipality', 'insee', '33002') == [
        mun1.id]


def test_modify_group_municipality(session):
    mun1 = factories.MunicipalityFactory(insee='33001', name='Mun1')
    mun2 = factories.MunicipalityFactory(insee='33002', name='Mun2')
    gr = factories.GroupFactory(municipality=mun2, name='GrToto')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    gr = models.Group.select().where(models.Group.name == 'GrToto').first()
    assert gr.municipality == mun1


def test_create_group_area(session):
    mun1 = factories.MunicipalityFactory(insee='33001', name='Mun1')
    mun2 = factories.MunicipalityFactory(insee='33002', name='Mun2')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    gr = models.Group.select().where(models.Group.name == mun2.name).first()
    assert gr.municipality == mun1
    assert gr.version == 1
    assert gr.attributes == {'insee': mun2.insee}


def test_modify_postcode_municipality(session):
    mun1 = factories.MunicipalityFactory(insee='33001', name='Mun1')
    mun2 = factories.MunicipalityFactory(insee='33002', name='Mun2')
    pc = factories.PostCodeFactory(municipality=mun2, name='PC2')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    pc = models.PostCode.select().where(
        models.PostCode.name == 'PC2').first()
    assert pc.municipality == mun1
    assert pc.attributes == {'ligne6': 'TOTO'}


def test_modify_housenumber_ancestors(session):
    mun1 = factories.MunicipalityFactory(insee='33001', name='Mun1')
    mun2 = factories.MunicipalityFactory(insee='33002', name='Mun2')
    gr = factories.GroupFactory(municipality=mun2, name='GrToto')
    hn = factories.HouseNumberFactory(parent=gr, number='1')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    hn = models.HouseNumber.select().where(
        models.HouseNumber.number == '1').first()
    gr_area = models.Group.select().where(
        models.Group.name == mun2.name).first()
    assert hn.ancestors == gr_area


def test_modify_destination_name(session):
    mun1 = factories.MunicipalityFactory(insee='33001', name='Mun1')
    mun2 = factories.MunicipalityFactory(insee='33002', name='Mun2')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    mun = models.Municipality.select().where(
        models.Municipality.insee == '33001').first()
    assert mun.name == 'Toto'


def test_delete_source(session):
    mun1 = factories.MunicipalityFactory(insee='33001', name='Mun1')
    mun2 = factories.MunicipalityFactory(insee='33002', name='Mun2')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    mun = models.Municipality.select().where(
        models.Municipality.insee == '33002').first()
    assert mun is None


def test_double_source_process_once(session):
    mun1 = factories.MunicipalityFactory(insee='33001', name='Mun1')
    mun2 = factories.MunicipalityFactory(insee='33002', name='Mun2')
    merge(mun1.insee,
          sources=[mun2.insee, mun2.insee], name='Toto', label='TOTO')
    gr = models.Group.select().where(models.Group.name == mun1.name)
    assert len(gr) == 1
    assert gr[0].version == 1
