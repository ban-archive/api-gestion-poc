from ban.core import models

from .factories import GroupFactory, MunicipalityFactory


def test_municipality_as_resource():
    municipality = MunicipalityFactory()
    assert list(models.Municipality.select().as_resource()) == [municipality.as_resource]  # noqa


def test_group_as_resource():
    street = GroupFactory()
    assert list(models.Group.select().as_resource()) == [street.as_resource]


def test_municipality_streets_as_resource():
    municipality = MunicipalityFactory()
    street = GroupFactory(municipality=municipality)
    assert list(municipality.groups.as_resource()) == [street.as_resource]
