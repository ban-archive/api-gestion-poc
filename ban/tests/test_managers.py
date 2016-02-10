from ban.core import models

from .factories import MunicipalityFactory, StreetFactory


def test_municipality_as_resource():
    municipality = MunicipalityFactory()
    assert list(models.Municipality.select().as_resource()) == [municipality.as_resource]  # noqa


def test_street_as_resource():
    street = StreetFactory()
    assert list(models.Street.select().as_resource()) == [street.as_resource]


def test_municipality_streets_as_resource():
    municipality = MunicipalityFactory()
    street = StreetFactory(municipality=municipality)
    assert list(municipality.streets.as_resource()) == [street.as_resource]
