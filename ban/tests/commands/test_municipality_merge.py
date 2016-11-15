import pytest

from ban.core import models
from ban.tests import factories
from ban.commands.municipality import merge
from ban.core import versioning


def test_unknown_destination_is_aborted():
    factories.MunicipalityFactory(insee='33001')
    with pytest.raises(SystemExit):
        merge('12345', sources=['33001'], name='Toto', label='TOTO')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1


def test_no_sources_is_aborted():
    factories.MunicipalityFactory(insee='33001', name='Toto', label='TOTO')
    with pytest.raises(SystemExit):
        merge('33001')


def test_unknown_source_is_aborted():
    factories.MunicipalityFactory(insee='33001')
    factories.MunicipalityFactory(insee='33002')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002', '33333'], name='Toto', label='TOTO')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1


def test_destination_in_sources_is_aborted():
    factories.MunicipalityFactory(insee='33001')
    factories.MunicipalityFactory(insee='33002')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002', '33001'], name='Toto', label='TOTO')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1


def test_no_name_is_aborted():
    factories.MunicipalityFactory(insee='33001')
    factories.MunicipalityFactory(insee='33002')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002'], label='TOTO')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1


def test_no_label_is_aborted():
    factories.MunicipalityFactory(insee='33001')
    factories.MunicipalityFactory(insee='33002')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002'], name='Toto')
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1


def test_redirect(session):
    mun1 = factories.MunicipalityFactory(insee='33001')
    mun2 = factories.MunicipalityFactory(insee='33002')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    assert versioning.Redirect.select().count() == 1
    assert versioning.Redirect.follow('Municipality', 'insee', '33002') == [
        mun1.id]


def test_modify_group_municipality(session):
    mun1 = factories.MunicipalityFactory(insee='33001')
    mun2 = factories.MunicipalityFactory(insee='33002')
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


def test_modify_postcode_municipality(session):
    mun1 = factories.MunicipalityFactory(insee='33001')
    mun2 = factories.MunicipalityFactory(insee='33002')
    pc = factories.PostCodeFactory(municipality=mun2, name='PCToto')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    pc = models.PostCode.select().where(
        models.PostCode.name == 'PCToto').first()
    assert pc.municipality == mun1


def test_modify_housenumber_ancestors(session):
    mun1 = factories.MunicipalityFactory(insee='33001')
    mun2 = factories.MunicipalityFactory(insee='33002')
    gr = factories.GroupFactory(municipality=mun2, name='GrToto')
    hn = factories.HouseNumberFactory(parent=gr, number='1')
    merge(mun1.insee, sources=[mun2.insee], name='Toto', label='TOTO')
    hn = models.HouseNumber.select().where(
        models.HouseNumber.number == '1').first()
    gr_area = models.Group.select().where(
        models.Group.name == mun2.name).first()
    assert hn.ancestors == gr_area
