import pytest

from ban.core import models
from ban.auth.models import User

from .factories import (GroupFactory, HouseNumberFactory, MunicipalityFactory,
                        PositionFactory)


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
    with pytest.raises(ValueError):
        validator.save()


def test_cannot_create_municipality_with_insee_too_short(session):
    validator = models.Municipality.validator(name="Eu", insee="1234",
                                              siren="12345678")
    assert 'insee' in validator.errors


def test_cannot_create_municipality_with_insee_too_long(session):
    validator = models.Municipality.validator(name="Eu", insee="123456",
                                              siren="12345678")
    assert 'insee' in validator.errors


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


def test_cannot_update_municipality_with_null_version(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Municipality.validator(instance=municipality,
                                              update=True, version=None,
                                              insee="54321")
    assert validator.errors['version'] == 'Value should not be null'


def test_cannot_update_municipality_with_empty_version(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Municipality.validator(instance=municipality,
                                              update=True, version='',
                                              insee="54321")
    assert validator.errors['version'] == 'Value should not be null'


def test_cannot_update_municipality_with_version_equal_to_0(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Municipality.validator(instance=municipality,
                                              update=True, version=0,
                                              insee="54321")
    assert validator.errors['version'] == 'Value should not be null'


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
                                          kind=models.Position.ENTRANCE,
                                          positioning=models.Position.IMAGERY,
                                          center=(1, 2))
    assert not validator.errors
    position = validator.save()
    assert position.center == (1, 2)
    assert position.housenumber == housenumber


def test_can_update_position(session):
    position = PositionFactory(center=(1, 2))
    validator = models.Position.validator(instance=position, update=True,
                                          housenumber=position.housenumber,
                                          center=(3, 4), version=2)
    assert not validator.errors
    position = validator.save()
    assert len(models.Position.select()) == 1
    assert position.center == (3, 4)
    assert position.version == 2


def test_can_create_position_with_parent(session):
    housenumber = HouseNumberFactory()
    parent = PositionFactory(housenumber=housenumber)
    validator = models.Position.validator(housenumber=housenumber,
                                          kind=models.Position.ENTRANCE,
                                          positioning=models.Position.IMAGERY,
                                          parent=parent, center=(1, 2))
    assert not validator.errors
    position = validator.save()
    assert position.parent == parent


def test_cannot_create_position_without_positioning(session):
    housenumber = HouseNumberFactory()
    parent = PositionFactory(housenumber=housenumber)
    validator = models.Position.validator(housenumber=housenumber,
                                          kind=models.Position.ENTRANCE,
                                          parent=parent, center=(1, 2))
    assert 'positioning' in validator.errors


def test_cannot_create_position_without_kind(session):
    housenumber = HouseNumberFactory()
    validator = models.Position.validator(housenumber=housenumber,
                                          positioning=models.Position.IMAGERY,
                                          center=(1, 2))
    assert 'kind' in validator.errors


def test_invalid_point_should_raise_an_error(session):
    housenumber = HouseNumberFactory()
    validator = models.Position.validator(housenumber=housenumber,
                                          positioning=models.Position.IMAGERY,
                                          center=1)
    assert 'center' in validator.errors


def test_can_create_postcode(session):
    municipality = MunicipalityFactory(insee='12345')
    validator = models.PostCode.validator(code="31310", name="Montbrun-Bocage",
                                          municipality=municipality)
    postcode = validator.save()
    assert postcode.code == "31310"


def test_can_create_postcode_with_integer(session):
    municipality = MunicipalityFactory(insee='12345')
    validator = models.PostCode.validator(code=31310, name="Montbrun-Bocage",
                                          municipality=municipality)
    postcode = validator.save()
    assert postcode.code == "31310"


def test_cannot_create_postcode_with_code_shorter_than_5_chars(session):
    municipality = MunicipalityFactory(insee='12345')
    validator = models.PostCode.validator(code="3131", name="Montbrun-Bocage",
                                          municipality=municipality)
    assert validator.errors['code'] == 'Invalid postcode: `3131`'


def test_cannot_create_postcode_with_code_bigger_than_5_chars(session):
    municipality = MunicipalityFactory(insee='12345')
    validator = models.PostCode.validator(code="313100", name="Montbrun",
                                          municipality=municipality)
    assert validator.errors['code'] == 'Invalid postcode: `313100`'


def test_cannot_create_postcode_with_code_non_digit(session):
    municipality = MunicipalityFactory(insee='12345')
    validator = models.PostCode.validator(code="2A000", name="Montbrun-Bocage",
                                          municipality=municipality)
    assert validator.errors['code'] == 'Invalid postcode: `2A000`'


def test_can_create_street(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality=municipality,
                                       fantoir='123456789')
    assert not validator.errors
    street = validator.save()
    assert len(models.Group.select()) == 1
    assert street.fantoir == "123456789"
    assert street.version == 1


def test_cannot_create_group_without_kind(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Group.validator(name='Rue des Girafes',
                                       municipality=municipality,
                                       fantoir='123456789')
    assert validator.errors


def test_can_create_group_with_fantoir_on_9digits(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality=municipality,
                                       fantoir='123456789')
    assert not validator.errors
    assert validator.data['fantoir'] == "123456789"


def test_can_create_group_with_fantoir_on_10digits(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality=municipality,
                                       fantoir='1234567890')
    assert not validator.errors
    assert validator.data['fantoir'] == "123456789"


def test_cannot_create_group_with_fantoir_less_than_9or10_digits(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality=municipality,
                                       fantoir='1234')
    assert 'fantoir' in validator.errors


def test_cannot_create_group_with_fantoir_greater_than_9or10_digits(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality=municipality,
                                       fantoir='123456789012')
    assert validator.errors['fantoir'] == ('FANTOIR must be municipality INSEE'
                                           ' + 4 first chars of FANTOIR, got '
                                           '`123456789012` instead')


def test_can_create_street_with_municipality_insee(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality='insee:12345',
                                       fantoir='123456789')
    assert not validator.errors
    street = validator.save()
    assert len(models.Group.select()) == 1
    assert street.fantoir == "123456789"
    assert street.version == 1
    assert street.municipality == municipality


def test_old_insee_return_an_error_with_new_identifier(session):
    municipality = MunicipalityFactory(insee="12345")
    # This should create a redirect.
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    # Call it with old insee.
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality='insee:12345',
                                       fantoir='123456789')
    assert 'municipality' in validator.errors
    assert municipality.id in validator.errors['municipality']


def test_can_create_street_with_empty_laposte_id(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality=municipality,
                                       laposte=None)
    assert not validator.errors
    street = validator.save()
    assert street.laposte is None


def test_can_create_street_with_falsy_laposte(session):
    municipality = MunicipalityFactory(insee="12345")
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality=municipality,
                                       laposte='')
    assert not validator.errors
    street = validator.save()
    assert models.Group.get(models.Group.pk == street.pk).laposte is None


def test_bad_foreign_key_gives_readable_message(session):
    validator = models.Group.validator(name='Rue des Girafes',
                                       kind=models.Group.WAY,
                                       municipality='insee:12345',
                                       fantoir='123456789')
    assert validator.errors['municipality'] == ('No matching resource for '
                                                '`insee:12345`')


def test_can_create_housenumber(session):
    street = GroupFactory()
    validator = models.HouseNumber.validator(parent=street, number='11')
    assert not validator.errors
    housenumber = validator.save()
    assert housenumber.number == '11'


def test_can_create_housenumber_with_ancestors(session):
    district = GroupFactory(name="IIIe arrondissement", kind=models.Group.AREA)
    street = GroupFactory()
    validator = models.HouseNumber.validator(parent=street, number='11',
                                             ancestors=[district])
    assert not validator.errors
    housenumber = validator.save()
    assert district in housenumber.ancestors


def test_can_create_housenumber_with_ancestor_ids(session):
    district = GroupFactory(name="IIIe arrondissement", kind=models.Group.AREA)
    street = GroupFactory()
    validator = models.HouseNumber.validator(parent=street, number='11',
                                             ancestors=[district.id])
    assert not validator.errors
    housenumber = validator.save()
    assert district in housenumber.ancestors


def test_can_update_housenumber_ancestor(session):
    district = GroupFactory(name="IIIe arrondissement", kind=models.Group.AREA)
    housenumber = HouseNumberFactory()
    validator = models.HouseNumber.validator(instance=housenumber,
                                             update=True,
                                             version=2,
                                             ancestors=[district])
    assert not validator.errors
    housenumber = validator.save()
    assert district in housenumber.ancestors


def test_giving_wrong_version_should_patch_if_possible(session):
    # Create an object.
    housenumber = HouseNumberFactory(number="18", ordinal=None)
    # Update one field.
    resource = housenumber.as_resource
    resource['number'] = "19"
    resource['version'] = 2
    validator = models.HouseNumber.validator(instance=housenumber, update=True,
                                             **resource)
    assert not validator.errors
    validator.save()
    # Update another field and give again version=2 as if we were only aware
    # of version 1.
    resource['number'] = "18"  # Pretend we haven't changed it.
    resource['ordinal'] = 'bis'
    resource['version'] = 2
    validator = models.HouseNumber.validator(instance=housenumber, update=True,
                                             **resource)
    assert not validator.errors
    housenumber = validator.save()
    assert housenumber.number == "19"
    assert housenumber.ordinal == "bis"


def test_giving_wrong_version_should_patch_if_possible_with_update(session):
    # Create an object.
    housenumber = HouseNumberFactory(number="18", ordinal=None)
    # Update one field.
    validator = models.HouseNumber.validator(instance=housenumber,
                                             update=True,
                                             version=2,
                                             number="19")
    validator.save()
    # Update another field and give again version=2.
    validator = models.HouseNumber.validator(instance=housenumber,
                                             update=True,
                                             version=2,
                                             ordinal="bis")
    assert not validator.errors
    housenumber = validator.save()
    assert housenumber.number == "19"
    assert housenumber.ordinal == "bis"


def test_can_create_user():
    validator = User.validator(username='Banner', email='ban@er',
                               is_staff=False)
    assert not validator.errors


def test_cannot_add_a_deleted_resource_as_fk():
    deleted = MunicipalityFactory()
    deleted.mark_deleted()
    validator = models.Group.validator(municipality=deleted,
                                       name='Rue des Pianos',
                                       kind=models.Group.AREA)
    assert validator.errors['municipality'] == (
        'Resource `municipality` with id `{}` is deleted'.format(deleted.id))


def test_cannot_add_a_deleted_resource_in_m2m():
    housenumber = HouseNumberFactory()
    deleted = GroupFactory()
    deleted.mark_deleted()
    validator = models.HouseNumber.validator(instance=housenumber, update=True,
                                             ancestors=[deleted], version=2)
    assert validator.errors['ancestors'] == (
        'Resource `group` with id `{}` is deleted'.format(deleted.id))
