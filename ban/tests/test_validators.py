import pytest

from ban.core import models

from .factories import (DistrictFactory, HouseNumberFactory,
                        MunicipalityFactory, PositionFactory, StreetFactory)


def test_can_create_municipality(session):
    validator = models.Municipality.validator(name="Eu", insee="12345",
                                              siren="12345678")
    assert not validator.errors
    municipality = validator.save()
    assert municipality.name == "Eu"
    assert municipality.insee == "12345"
    assert municipality.siren == "12345678"


def test_can_create_municipality_with_version(session):
    validator = models.Municipality.validator(name="Eu", insee="12345",
                                              siren="12345678", version=1)
    assert not validator.errors
    municipality = validator.save()
    assert municipality.id


def test_create_should_not_consider_bad_versions(session):
    validator = models.Municipality.validator(name="Eu", insee="12345",
                                              siren="12345678", version=10)
    assert not validator.errors
    municipality = validator.save()
    assert municipality.id
    assert municipality.version == 1


def test_cannot_create_municipality_with_missing_fields(session):
    validator = models.Municipality.validator(name="Eu")
    assert validator.errors
    with pytest.raises(validator.ValidationError):
        validator.save()


def test_can_update_municipality(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Municipality.validator(instance=municipality,
                                              name=municipality.name,
                                              siren=municipality.siren,
                                              insee="54321", version=2)
    assert not validator.errors
    municipality = validator.save()
    assert len(models.Municipality.select()) == 1
    assert municipality.insee == "54321"
    assert municipality.version == 2


def test_cannot_update_municipality_without_version(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Municipality.validator(instance=municipality,
                                              update=True,
                                              insee="54321")
    assert 'version' in validator.errors


def test_cannot_duplicate_municipality_insee(session):
    MunicipalityFactory(insee='12345')
    validator = models.Municipality.validator(name='Carbone',
                                              siren='123456789',
                                              insee="12345", version=2)
    assert 'insee' in validator.errors
    assert '12345' in validator.errors['insee']


def test_can_create_municipality_with_alias(session):
    validator = models.Municipality.validator(name="Orvane",
                                              alias=["Moret-sur-Loing"],
                                              insee="12345",
                                              siren="12345678")
    assert not validator.errors
    municipality = validator.save()
    assert 'Moret-sur-Loing' in municipality.alias


def test_can_create_position(session):
    housenumber = HouseNumberFactory()
    validator = models.Position.validator(housenumber=housenumber,
                                          center=(1, 2))
    assert not validator.errors
    position = validator.save()
    assert position.center == (1, 2)
    assert position.housenumber == housenumber


def test_can_update_position(session):
    position = PositionFactory(center=(1, 2))
    validator = models.Position.validator(instance=position,
                                          housenumber=position.housenumber,
                                          center=(3, 4), version=2)
    assert not validator.errors
    position = validator.save()
    assert len(models.Position.select()) == 1
    assert position.center == (3, 4)
    assert position.version == 2


def test_can_create_postcode(session):
    validator = models.PostCode.validator(code="31310")
    postcode = validator.save()
    assert postcode.code == "31310"


def test_can_create_postcode_with_integer(session):
    validator = models.PostCode.validator(code=31310)
    postcode = validator.save()
    assert postcode.code == "31310"


def test_cannot_create_postcode_with_code_shorter_than_5_chars(session):
    validator = models.PostCode.validator(code="3131")
    assert 'code' in validator.errors


def test_cannot_create_postcode_with_code_bigger_than_5_chars(session):
    validator = models.PostCode.validator(code="313100")
    assert 'code' in validator.errors


def test_cannot_create_postcode_with_code_non_digit(session):
    validator = models.PostCode.validator(code="2A000")
    assert 'code' in validator.errors


def test_can_create_street(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Street.validator(name='Rue des Girafes',
                                        municipality=municipality,
                                        fantoir='123456789')
    assert not validator.errors
    street = validator.save()
    assert len(models.Street.select()) == 1
    assert street.fantoir == "123456789"
    assert street.version == 1


def test_can_create_street_with_municipality_insee(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Street.validator(name='Rue des Girafes',
                                        municipality='insee:12345',
                                        fantoir='123456789')
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
                                        fantoir='123456789')
    assert not validator.errors
    street = validator.save()
    assert len(models.Street.select()) == 1
    assert street.municipality == municipality


def test_can_create_housenumber(session):
    street = StreetFactory()
    validator = models.HouseNumber.validator(street=street, number='11')
    assert not validator.errors
    housenumber = validator.save()
    assert housenumber.number == '11'


def test_can_create_housenumber_with_district(session):
    district = DistrictFactory()
    street = StreetFactory()
    validator = models.HouseNumber.validator(street=street, number='11',
                                             districts=[district])
    assert not validator.errors
    housenumber = validator.save()
    assert district in housenumber.districts


def test_can_create_housenumber_with_district_ids(session):
    district = DistrictFactory()
    street = StreetFactory()
    validator = models.HouseNumber.validator(street=street, number='11',
                                             districts=[district.id])
    assert not validator.errors
    housenumber = validator.save()
    assert district in housenumber.districts


def test_can_update_housenumber_district(session):
    district = DistrictFactory()
    housenumber = HouseNumberFactory()
    validator = models.HouseNumber.validator(instance=housenumber,
                                             update=True,
                                             version=2,
                                             districts=[district])
    assert not validator.errors
    housenumber = validator.save()
    assert district in housenumber.districts
