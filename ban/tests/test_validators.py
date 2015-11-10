import pytest

from ban.core import models

from .factories import (HouseNumberFactory, LocalityFactory,
                        MunicipalityFactory, PositionFactory, StreetFactory,
                        UserFactory)


def test_can_create_municipality():
    validator = models.Municipality.validator(name="Eu", insee="12345",
                                              siren="12345678", version=1)
    assert not validator.errors
    municipality = validator.save()
    assert municipality.name == "Eu"
    assert municipality.insee == "12345"
    assert municipality.siren == "12345678"


def test_can_create_municipality_with_missing_fields():
    validator = models.Municipality.validator(name="Eu")
    assert validator.errors
    with pytest.raises(validator.ValidationError):
        validator.save()


def test_can_update_municipality():
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Municipality.validator(name=municipality.name,
                                              siren=municipality.siren,
                                              insee="54321", version=2)
    assert not validator.errors
    municipality = validator.save(instance=municipality)
    assert len(models.Municipality.select()) == 1
    assert municipality.insee == "54321"
    assert municipality.version == 2


def test_can_create_position():
    housenumber = HouseNumberFactory()
    validator = models.Position.validator(housenumber=housenumber,
                                          center=(1, 2), version=1)
    assert not validator.errors
    position = validator.save()
    assert position.center == (1, 2)
    assert position.housenumber == housenumber


def test_can_update_position():
    position = PositionFactory(center=(1, 2))
    validator = models.Position.validator(housenumber=position.housenumber,
                                          center=(3, 4), version=2)
    assert not validator.errors
    position = validator.save(position)
    assert len(models.Position.select()) == 1
    assert position.center == (3, 4)
    assert position.version == 2
