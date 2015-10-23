import pytest

from .factories import (MunicipalityFactory, StreetFactory)

from ban.core import models

pytestmark = pytest.mark.django_db


def test_municipality_public_data():
    municipality = MunicipalityFactory()
    assert list(models.Municipality.objects.public_data) == [municipality.public_data]  # noqa


def test_street_public_data():
    street = StreetFactory()
    assert list(models.Street.objects.public_data) == [street.public_data]


def test_municipality_street_public_data():
    municipality = MunicipalityFactory()
    street = StreetFactory(municipality=municipality)
    assert list(municipality.street_set.public_data) == [street.public_data]
