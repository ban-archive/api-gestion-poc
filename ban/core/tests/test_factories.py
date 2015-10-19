import pytest

from .factories import (HouseNumberFactory, MunicipalityFactory,
                        PositionFactory, StreetFactory, UserFactory)

pytestmark = pytest.mark.django_db


def test_user_can_be_instanciated():
    user = UserFactory()
    assert user.is_active


def test_municipality_can_be_instanciated():
    municipality = MunicipalityFactory()
    assert municipality.name


def test_street_can_be_instanciated():
    street = StreetFactory()
    assert street.name


def test_housenumber_can_be_instanciated():
    hn = HouseNumberFactory()
    assert hn.number


def test_position_can_be_instanciated():
    position = PositionFactory()
    assert position.center
