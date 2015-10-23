import pytest

from ban.core import models

from .factories import MunicipalityFactory, StreetFactory

pytestmark = pytest.mark.django_db


def test_municipality_as_resource():
    municipality = MunicipalityFactory()
    assert list(models.Municipality.objects.as_resource) == [municipality.as_resource]  # noqa


def test_street_as_resource():
    street = StreetFactory()
    assert list(models.Street.objects.as_resource) == [street.as_resource]


def test_municipality_street_as_resource():
    municipality = MunicipalityFactory()
    street = StreetFactory(municipality=municipality)
    assert list(municipality.street_set.as_resource) == [street.as_resource]
