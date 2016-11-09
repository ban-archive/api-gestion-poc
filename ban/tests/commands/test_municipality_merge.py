import pytest

from ban.core import models
from ban.tests import factories
from ban.commands.municipality import merge


def test_unknown_destination_is_aborted():
    factories.MunicipalityFactory(insee='33001')
    with pytest.raises(SystemExit):
        merge('12345', sources=['33001'])
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1


def test_no_sources_is_aborted():
    factories.MunicipalityFactory(insee='33001')
    with pytest.raises(SystemExit):
        merge('33001')


def test_unknown_source_is_aborted():
    factories.MunicipalityFactory(insee='33001')
    factories.MunicipalityFactory(insee='33002')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002', '33333'])
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1


def test_destination_in_sources_is_aborted():
    factories.MunicipalityFactory(insee='33001')
    factories.MunicipalityFactory(insee='33002')
    with pytest.raises(SystemExit):
        merge('33001', sources=['33002', '33001'])
    mun = models.Municipality.get(models.Municipality.insee == '33001')
    assert mun.version == 1
    mun = models.Municipality.get(models.Municipality.insee == '33002')
    assert mun.version == 1
