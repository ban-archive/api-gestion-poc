import pytest
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError

from .factories import (HouseNumberFactory, MunicipalityFactory,
                        PositionFactory, StreetFactory)

pytestmark = pytest.mark.django_db


def test_municipality_is_created_with_version_1():
    municipality = MunicipalityFactory()
    assert municipality.version == 1


def test_municipality_is_versioned():
    initial_name = "Moret-sur-Loing"
    municipality = MunicipalityFactory(name=initial_name)
    assert municipality.version == 1
    municipality.name = "Orvanne"
    municipality.increment_version()
    municipality.save()
    assert municipality.version == 2
    assert len(municipality.versions) == 2
    version1 = municipality.versions[0].load()
    version2 = municipality.versions[1].load()
    assert version1.name == "Moret-sur-Loing"
    assert version2.name == "Orvanne"


def test_street_is_versioned():
    initial_name = "Rue des Pommes"
    street = StreetFactory(name=initial_name)
    assert street.version == 1
    street.name = "Rue des Poires"
    street.increment_version()
    street.save()
    assert street.version == 2
    assert len(street.versions) == 2
    version1 = street.versions[0].load()
    version2 = street.versions[1].load()
    assert version1.name == "Rue des Pommes"
    assert version2.name == "Rue des Poires"


def test_tmp_fantoir_should_use_name():
    municipality = MunicipalityFactory(insee='93031')
    street = StreetFactory(municipality=municipality, fantoir='',
                           name="Rue des Pêchers")
    assert street.tmp_fantoir == '#RUEDESPECHERS'


def test_compute_cia_should_consider_insee_fantoir_number_and_ordinal():
    municipality = MunicipalityFactory(insee='93031')
    street = StreetFactory(municipality=municipality, fantoir='1491H')
    hn = HouseNumberFactory(street=street, number="84", ordinal="bis")
    assert hn.compute_cia() == '93031_1491H_84_BIS'


def test_compute_cia_should_let_ordinal_empty_if_not_set():
    municipality = MunicipalityFactory(insee='93031')
    street = StreetFactory(municipality=municipality, fantoir='1491H')
    hn = HouseNumberFactory(street=street, number="84", ordinal="")
    assert hn.compute_cia() == '93031_1491H_84_'


def test_housenumber_should_create_cia_on_save():
    municipality = MunicipalityFactory(insee='93031')
    street = StreetFactory(municipality=municipality, fantoir='1491H')
    hn = HouseNumberFactory(street=street, number="84", ordinal="bis")
    assert hn.cia == '93031_1491H_84_BIS'


def test_housenumber_is_versioned():
    street = StreetFactory()
    hn = HouseNumberFactory(street=street, ordinal="b")
    assert hn.version == 1
    hn.ordinal = "bis"
    hn.increment_version()
    hn.save()
    assert hn.version == 2
    assert len(hn.versions) == 2
    version1 = hn.versions[0].load()
    version2 = hn.versions[1].load()
    assert version1.ordinal == "b"
    assert version2.ordinal == "bis"
    assert version2.street == street


def test_cannot_duplicate_housenumber_on_same_street():
    street = StreetFactory()
    HouseNumberFactory(street=street, ordinal="b", number="10")
    with pytest.raises(ValidationError):
        HouseNumberFactory(street=street, ordinal="b", number="10")


def test_can_create_two_housenumbers_with_same_number_but_different_street():
    street = StreetFactory()
    street2 = StreetFactory()
    HouseNumberFactory(street=street, ordinal="b", number="10")
    HouseNumberFactory(street=street2, ordinal="b", number="10")


def test_position_is_versioned():
    housenumber = HouseNumberFactory()
    position = PositionFactory(housenumber=housenumber, center=Point(1, 2))
    assert position.version == 1
    position.center = Point(3, 4)
    position.increment_version()
    position.save()
    assert position.version == 2
    assert len(position.versions) == 2
    version1 = position.versions[0].load()
    version2 = position.versions[1].load()
    assert version1.center.coords == (1, 2)
    assert version2.center.coords == (3, 4)
    assert version2.housenumber == housenumber
