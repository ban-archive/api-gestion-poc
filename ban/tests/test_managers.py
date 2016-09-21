from ban.core import models

from .factories import GroupFactory, MunicipalityFactory


def test_municipality_serialize():
    municipality = MunicipalityFactory()
    assert list(models.Municipality.select().serialize()) == [municipality.serialize()]  # noqa


def test_group_as_resource():
    street = GroupFactory()
    assert list(models.Group.select().serialize()) == [street.serialize()]


def test_municipality_streets_as_resource():
    municipality = MunicipalityFactory()
    street = GroupFactory(municipality=municipality)
    assert list(municipality.groups.serialize()) == [street.serialize()]
