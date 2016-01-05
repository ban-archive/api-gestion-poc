import peewee
import pytest

from ban.core import models

from .factories import (DistrictFactory, HouseNumberFactory,
                        MunicipalityFactory, PositionFactory, PostCodeFactory,
                        StreetFactory)


def test_municipality_is_created_with_version_1():
    municipality = MunicipalityFactory()
    assert municipality.version == 1


def test_municipality_is_versioned():
    municipality = MunicipalityFactory(name="Moret-sur-Loing")
    assert len(municipality.versions) == 1
    assert municipality.version == 1
    municipality.name = "Orvanne"
    municipality.increment_version()
    municipality.save()
    assert municipality.version == 2
    assert len(municipality.versions) == 2
    version1 = municipality.versions[0].load()
    version2 = municipality.versions[1].load()
    assert version1.name == "Moret-sur-Loing"
    assert version2.name == "Orvanne"
    assert municipality.versions[0].diff
    diff = municipality.versions[1].diff
    assert len(diff.diff) == 1  # name, version
    assert diff.diff['name']['new'] == "Orvanne"
    municipality.insee = "77316"
    municipality.increment_version()
    municipality.save()
    assert len(municipality.versions) == 3
    diff = municipality.versions[2].diff
    assert diff.old == municipality.versions[1]
    assert diff.new == municipality.versions[2]


def test_municipality_diff_contain_only_changed_data():
    municipality = MunicipalityFactory(name="Moret-sur-Loing", insee="77316")
    municipality.name = "Orvanne"
    # "Changed" with same value.
    municipality.insee = "77316"
    municipality.increment_version()
    municipality.save()
    diff = municipality.versions[1].diff
    assert len(diff.diff) == 1  # name, version
    assert 'insee' not in diff.diff
    assert diff.diff['name']['new'] == "Orvanne"


def test_municipality_postcodes():
    postcode1 = PostCodeFactory(code="75010")
    postcode2 = PostCodeFactory(code="75011")
    municipality = MunicipalityFactory(name="Paris")
    municipality.postcodes.add(postcode1)
    municipality.postcodes.add(postcode2)
    postcodes = municipality.postcodes
    assert len(postcodes) == 2
    assert postcode1 in postcodes
    assert postcode2 in postcodes


def test_postcode_municipalities():
    postcode = PostCodeFactory(code="31310")
    municipality1 = MunicipalityFactory(name="Montbrun-Bocage")
    municipality2 = MunicipalityFactory(name="Montesquieu-Volvestre")
    municipality1.postcodes.add(postcode)
    municipality2.postcodes.add(postcode)
    assert municipality1 in postcode.municipalities
    assert municipality2 in postcode.municipalities


def test_municipality_as_resource():
    municipality = MunicipalityFactory(name="Montbrun-Bocage", insee="31365",
                                       siren="210100566")
    postcode = PostCodeFactory(code="31310")
    municipality.postcodes.add(postcode)
    assert municipality.as_resource['name'] == "Montbrun-Bocage"
    assert municipality.as_resource['insee'] == "31365"
    assert municipality.as_resource['siren'] == "210100566"
    assert municipality.as_resource['version'] == 1
    assert municipality.as_resource['id'] == municipality.id
    assert municipality.as_resource['postcodes'] == ['31310']


def test_municipality_as_relation():
    municipality = MunicipalityFactory(name="Montbrun-Bocage", insee="31365",
                                       siren="210100566")
    postcode = PostCodeFactory(code="31310")
    municipality.postcodes.add(postcode)
    assert municipality.as_relation['name'] == "Montbrun-Bocage"
    assert municipality.as_relation['insee'] == "31365"
    assert municipality.as_relation['siren'] == "210100566"
    assert municipality.as_relation['id'] == municipality.id
    assert 'postcodes' not in municipality.as_relation
    assert 'version' not in municipality.as_relation


def test_municipality_str():
    municipality = MunicipalityFactory(name="Salsein")
    assert str(municipality) == 'Salsein'


@pytest.mark.parametrize('factory,kwargs', [
    (MunicipalityFactory, {'insee': '12345'}),
    (MunicipalityFactory, {'siren': '123456789'}),
])
def test_unique_fields(factory, kwargs):
    factory(**kwargs)
    with pytest.raises(peewee.IntegrityError):
        factory(**kwargs)


def test_should_allow_deleting_municipality_not_linked():
    municipality = MunicipalityFactory()
    municipality.delete_instance()
    assert not models.Municipality.select().count()


def test_should_not_allow_deleting_municipality_linked_to_street():
    municipality = MunicipalityFactory()
    StreetFactory(municipality=municipality)
    with pytest.raises(peewee.IntegrityError):
        municipality.delete_instance()
    assert models.Municipality.get(models.Municipality.id == municipality.id)


def test_street_is_versioned():
    initial_name = "Rue des Pommes"
    street = StreetFactory(name=initial_name)
    assert street.version == 1
    street.name = "Rue des Poires"
    street.increment_version()
    street.save()
    assert street.version == 2
    assert len(street.versions) == 2
    version1 = street.versions[0].load()
    version2 = street.versions[1].load()
    assert version1.name == "Rue des Pommes"
    assert version2.name == "Rue des Poires"
    assert street.versions[0].diff
    diff = street.versions[1].diff
    assert len(diff.diff) == 1  # name, version
    assert diff.diff['name']['new'] == "Rue des Poires"


def test_should_allow_deleting_street_not_linked():
    street = StreetFactory()
    street.delete_instance()
    assert not models.Street.select().count()


def test_should_not_allow_deleting_street_linked_to_housenumber():
    street = StreetFactory()
    HouseNumberFactory(street=street)
    with pytest.raises(peewee.IntegrityError):
        street.delete_instance()
    assert models.Street.get(models.Street.id == street.id)


def test_tmp_fantoir_should_use_name():
    municipality = MunicipalityFactory(insee='93031')
    street = StreetFactory(municipality=municipality, fantoir='',
                           name="Rue des Pêchers")
    assert street.tmp_fantoir == '#RUEDESPECHERS'


def test_compute_cia_should_consider_insee_fantoir_number_and_ordinal():
    municipality = MunicipalityFactory(insee='93031')
    street = StreetFactory(municipality=municipality, fantoir='1491H')
    hn = HouseNumberFactory(street=street, number="84", ordinal="bis")
    assert hn.compute_cia() == '93031_1491H__84_BIS'


def test_compute_cia_should_let_ordinal_empty_if_not_set():
    municipality = MunicipalityFactory(insee='93031')
    street = StreetFactory(municipality=municipality, fantoir='1491H')
    hn = HouseNumberFactory(street=street, number="84", ordinal="")
    assert hn.compute_cia() == '93031_1491H__84_'


def test_compute_cia_should_use_locality_if_no_street():
    municipality = MunicipalityFactory(insee='93031')
    street = StreetFactory(municipality=municipality, fantoir='1491H')
    hn = HouseNumberFactory(street=street, number="84", ordinal="")
    assert hn.compute_cia() == '93031_1491H__84_'


def test_housenumber_should_create_cia_on_save():
    municipality = MunicipalityFactory(insee='93031')
    street = StreetFactory(municipality=municipality, fantoir='1491H')
    hn = HouseNumberFactory(street=street, number="84", ordinal="bis")
    assert hn.cia == '93031_1491H__84_BIS'


def test_housenumber_is_versioned():
    street = StreetFactory()
    hn = HouseNumberFactory(street=street, ordinal="b")
    assert hn.version == 1
    hn.ordinal = "bis"
    hn.increment_version()
    hn.save()
    assert hn.version == 2
    assert len(hn.versions) == 2
    version1 = hn.versions[0].load()
    version2 = hn.versions[1].load()
    assert version1.ordinal == "b"
    assert version2.ordinal == "bis"
    assert version2.street == street


def test_cannot_duplicate_housenumber_on_same_street():
    street = StreetFactory()
    HouseNumberFactory(street=street, ordinal="b", number="10")
    with pytest.raises(ValueError):
        HouseNumberFactory(street=street, ordinal="b", number="10")


def test_cannot_create_housenumber_without_street_and_locality():
    with pytest.raises(ValueError):
        HouseNumberFactory(street=None, locality=None)


def test_housenumber_str():
    hn = HouseNumberFactory(ordinal="b", number="10")
    assert str(hn) == '10 b'


def test_can_create_two_housenumbers_with_same_number_but_different_streets():
    street = StreetFactory()
    street2 = StreetFactory()
    HouseNumberFactory(street=street, ordinal="b", number="10")
    HouseNumberFactory(street=street2, ordinal="b", number="10")


def test_housenumber_center():
    housenumber = HouseNumberFactory()
    position = PositionFactory(housenumber=housenumber)
    assert housenumber.center == position.center_resource


def test_housenumber_center_without_position():
    housenumber = HouseNumberFactory()
    assert housenumber.center is None


def test_create_housenumber_with_district():
    municipality = MunicipalityFactory()
    district = DistrictFactory(municipality=municipality)
    housenumber = HouseNumberFactory(districts=[district],
                                     street__municipality=municipality)
    assert district in housenumber.districts
    assert housenumber in district.housenumbers


def test_add_district_to_housenumber():
    housenumber = HouseNumberFactory()
    district = DistrictFactory(municipality=housenumber.parent.municipality)
    housenumber.districts.add(district)
    assert district in housenumber.districts
    assert housenumber in district.housenumbers


def test_should_allow_deleting_housenumber_not_linked():
    housenumber = HouseNumberFactory()
    housenumber.delete_instance()
    assert not models.HouseNumber.select().count()


def test_should_not_allow_deleting_housenumber_not_linked():
    housenumber = HouseNumberFactory()
    PositionFactory(housenumber=housenumber)
    with pytest.raises(peewee.IntegrityError):
        housenumber.delete_instance()
    assert models.HouseNumber.get(models.HouseNumber.id == housenumber.id)


def test_position_is_versioned():
    housenumber = HouseNumberFactory()
    position = PositionFactory(housenumber=housenumber, center=(1, 2))
    assert position.version == 1
    position.center = (3, 4)
    position.increment_version()
    position.save()
    assert position.version == 2
    assert len(position.versions) == 2
    version1 = position.versions[0].load()
    version2 = position.versions[1].load()
    assert version1.center == [1, 2]  # json only knows about lists.
    assert version2.center == [3, 4]
    assert version2.housenumber == housenumber


def test_position_attributes():
    position = PositionFactory(attributes={'foo': 'bar'})
    assert position.attributes['foo'] == 'bar'
    assert models.Position.select().where(models.Position.attributes.contains({'foo': 'bar'})).exists()  # noqa


def test_get_instantiate_object_properly():
    original = PositionFactory()
    loaded = models.Position.get(models.Position.id == original.id)
    assert loaded.id == original.id
    assert loaded.version == original.version
    assert loaded.center == original.center
    assert loaded.housenumber == original.housenumber


@pytest.mark.parametrize('given,expected', [
    ((1, 2), (1, 2)),
    ((1.123456789, 2.987654321), (1.123456789, 2.987654321)),
    ([1, 2], (1, 2)),
    ("(1, 2)", (1, 2)),
])
def test_position_center_coerce(given, expected):
    position = PositionFactory(center=given)
    center = models.Position.get(models.Position.id == position.id).center
    assert center.coords == expected
