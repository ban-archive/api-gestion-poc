import pytest

from ban.core import models

from .factories import (HouseNumberFactory, LocalityFactory,
                        MunicipalityFactory, PositionFactory, StreetFactory,
                        UserFactory)


def test_can_create_municipality(session):
    validator = models.Municipality.validator(name="Eu", insee="12345",
                                              siren="12345678", version=1)
    assert not validator.errors
    municipality = validator.save()
    assert municipality.name == "Eu"
    assert municipality.insee == "12345"
    assert municipality.siren == "12345678"


def test_cannot_create_municipality_with_missing_fields(session):
    validator = models.Municipality.validator(name="Eu")
    assert validator.errors
    with pytest.raises(validator.ValidationError):
        validator.save()


def test_can_update_municipality(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Municipality.validator(name=municipality.name,
                                              siren=municipality.siren,
                                              insee="54321", version=2)
    assert not validator.errors
    municipality = validator.save(instance=municipality)
    assert len(models.Municipality.select()) == 1
    assert municipality.insee == "54321"
    assert municipality.version == 2


def test_can_create_position(session):
    housenumber = HouseNumberFactory()
    validator = models.Position.validator(housenumber=housenumber,
                                          center=(1, 2), version=1)
    assert not validator.errors
    position = validator.save()
    assert position.center == (1, 2)
    assert position.housenumber == housenumber


def test_can_update_position(session):
    position = PositionFactory(center=(1, 2))
    validator = models.Position.validator(housenumber=position.housenumber,
                                          center=(3, 4), version=2)
    assert not validator.errors
    position = validator.save(position)
    assert len(models.Position.select()) == 1
    assert position.center == (3, 4)
    assert position.version == 2


def test_can_create_zipcode(session):
    validator = models.ZipCode.validator(code="31310", version=1)
    zipcode = validator.save()
    assert zipcode.code == "31310"


def test_can_create_zipcode_with_integer(session):
    validator = models.ZipCode.validator(code=31310, version=1)
    zipcode = validator.save()
    assert zipcode.code == "31310"


def test_cannot_create_zipcode_with_code_shorter_than_5_chars(session):
    validator = models.ZipCode.validator(code="3131", version=1)
    assert 'code' in validator.errors


def test_cannot_create_zipcode_with_code_bigger_than_5_chars(session):
    validator = models.ZipCode.validator(code="313100", version=1)
    assert 'code' in validator.errors


def test_cannot_create_zipcode_with_code_non_digit(session):
    validator = models.ZipCode.validator(code="2A000", version=1)
    assert 'code' in validator.errors


def test_can_create_street(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Street.validator(name='Rue des Girafes',
                                        municipality=municipality,
                                        fantoir='123456789', version=1)
    assert not validator.errors
    street = validator.save()
    assert len(models.Street.select()) == 1
    assert street.fantoir == "123456789"
    assert street.version == 1


def test_can_create_street_with_municipality_insee(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Street.validator(name='Rue des Girafes',
                                        municipality='insee:12345',
                                        fantoir='123456789', version=1)
    assert not validator.errors
    street = validator.save()
    assert len(models.Street.select()) == 1
    assert street.fantoir == "123456789"
    assert street.version == 1
    assert street.municipality == municipality


def test_can_create_street_with_municipality_old_insee(session):
    municipality = MunicipalityFactory(insee="12345")
    # This should create a redirect.
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    # Call it with old insee.
    validator = models.Street.validator(name='Rue des Girafes',
                                        municipality='insee:12345',
                                        fantoir='123456789', version=1)
    assert not validator.errors
    street = validator.save()
    assert len(models.Street.select()) == 1
    assert street.municipality == municipality
