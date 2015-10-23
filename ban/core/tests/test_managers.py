import pytest

from .factories import (MunicipalityFactory, StreetFactory)

from ban.core import models

pytestmark = pytest.mark.django_db


def test_municipality_as_json():
    municipality = MunicipalityFactory()
    assert list(models.Municipality.objects.as_json) == [municipality.as_json]


def test_street_as_json():
    street = StreetFactory()
    assert list(models.Street.objects.as_json) == [street.as_json]


def test_municipality_street_as_json():
    municipality = MunicipalityFactory()
    street = StreetFactory(municipality=municipality)
    assert list(municipality.street_set.as_json) == [street.as_json]
