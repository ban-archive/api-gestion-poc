import datetime

import peewee
import pytest

from ban.core import models

from .factories import (GroupFactory, HouseNumberFactory, MunicipalityFactory,
                        PositionFactory, PostCodeFactory)


def test_get_model_locks_version():
    m = MunicipalityFactory()
    municipality = models.Municipality.get(models.Municipality.pk == m.pk)
    assert municipality._locked_version == 1


def test_select_first_model_locks_version():
    MunicipalityFactory()
    municipality = models.Municipality.select().first()
    assert municipality._locked_version == 1


def test_created_at_is_utc_aware():
    MunicipalityFactory()
    municipality = models.Municipality.select().first()
    assert municipality.created_at.tzinfo == datetime.timezone.utc


def test_municipality_is_created_with_version_1():
    municipality = MunicipalityFactory()
    assert municipality.version == 1


def test_municipality_postcodes():
    municipality = MunicipalityFactory(name="Paris")
    postcode1 = PostCodeFactory(code="75010", municipality=municipality)
    postcode2 = PostCodeFactory(code="75011", municipality=municipality)
    postcodes = municipality.postcodes
    assert len(postcodes) == 2
    assert postcode1 in postcodes
    assert postcode2 in postcodes


def test_municipality_as_resource():
    municipality = MunicipalityFactory(name="Montbrun-Bocage", insee="31365",
                                       siren="210100566")
    postcode = PostCodeFactory(code="31310", municipality=municipality)

    assert municipality.as_resource['name'] == "Montbrun-Bocage"
    assert municipality.as_resource['insee'] == "31365"
    assert municipality.as_resource['siren'] == "210100566"
    assert municipality.as_resource['version'] == 1
    assert municipality.as_resource['id'] == municipality.id
    assert municipality.as_resource['postcodes'] == [{
        'code': '31310',
        'attributes': None,
        'resource': 'postcode',
        'name': 'Test PostCode Area Name',
        'municipality': municipality.id,
        'id': postcode.id,
        'alias': None,
        'version': 1,
    }]


def test_municipality_as_relation():
    municipality = MunicipalityFactory(name="Montbrun-Bocage", insee="31365",
                                       siren="210100566")
    PostCodeFactory(code="31310", municipality=municipality)
    assert municipality.as_relation['name'] == "Montbrun-Bocage"
    assert municipality.as_relation['insee'] == "31365"
    assert municipality.as_relation['siren'] == "210100566"
    assert municipality.as_relation['id'] == municipality.id
    assert 'postcodes' not in municipality.as_relation


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
    GroupFactory(municipality=municipality)
    with pytest.raises(peewee.IntegrityError):
        municipality.delete_instance()
    assert models.Municipality.get(models.Municipality.id == municipality.id)


def test_should_allow_deleting_street_not_linked():
    street = GroupFactory()
    street.delete_instance()
    assert not models.Group.select().count()


def test_should_not_allow_deleting_street_linked_to_housenumber():
    street = GroupFactory()
    HouseNumberFactory(parent=street)
    with pytest.raises(peewee.IntegrityError):
        street.delete_instance()
    assert models.Group.get(models.Group.id == street.id)


def test_tmp_fantoir_should_use_name():
    municipality = MunicipalityFactory(insee='93031')
    street = GroupFactory(municipality=municipality, fantoir='',
                          name="Rue des Pêchers")
    assert street.tmp_fantoir == '#RUEDESPECHERS'


def test_compute_cia_should_consider_insee_fantoir_number_and_ordinal():
    municipality = MunicipalityFactory(insee='93031')
    street = GroupFactory(municipality=municipality, fantoir='930311491')
    hn = HouseNumberFactory(parent=street, number="84", ordinal="bis")
    hn = models.HouseNumber.get(models.HouseNumber.id == hn.id)
    assert hn.compute_cia() == '93031_1491_84_BIS'


def test_compute_cia_should_let_ordinal_empty_if_not_set():
    municipality = MunicipalityFactory(insee='93031')
    street = GroupFactory(municipality=municipality, fantoir='930311491')
    hn = HouseNumberFactory(parent=street, number="84", ordinal="")
    assert hn.compute_cia() == '93031_1491_84_'


def test_compute_cia_should_use_locality_if_no_street():
    municipality = MunicipalityFactory(insee='93031')
    street = GroupFactory(municipality=municipality, fantoir='930311491')
    hn = HouseNumberFactory(parent=street, number="84", ordinal="")
    assert hn.compute_cia() == '93031_1491_84_'


def test_group_as_relation():
    municipality = MunicipalityFactory()
    street = GroupFactory(municipality=municipality, name="Rue des Fleurs",
                          fantoir="930311491")
    data = street.as_relation
    assert data == {
        'id': street.id,
        'municipality': municipality.id,
        'kind': 'way',
        'fantoir': '930311491',
        'alias': None,
        'ign': None,
        'name': 'Rue des Fleurs',
        'resource': 'group',
        'attributes': None,
        'laposte': None,
        'addressing': None,
        'version': 1
    }


def test_can_create_group_with_fantoir_equal_to_9_chars(get):
    fantoir = "900010123"
    group = GroupFactory(fantoir=fantoir)
    assert group.fantoir == fantoir


def test_can_create_group_with_fantoir_equal_to_10_chars(get):
    fantoir = "7800101234"
    group = GroupFactory(fantoir=fantoir)
    assert group.fantoir == fantoir[:9]


def test_cannot_create_group_with_fantoir_less_than_9_or_10_chars():
    fantoir = "90001012"
    with pytest.raises(ValueError):
        GroupFactory(fantoir=fantoir)


def test_cannot_create_group_with_fantoir_greater_than_9_or_10_chars():
    fantoir = "900010123456"
    with pytest.raises(ValueError):
        GroupFactory(fantoir=fantoir)


def test_housenumber_should_create_cia_on_save():
    municipality = MunicipalityFactory(insee='93031')
    street = GroupFactory(municipality=municipality, fantoir='930311491')
    hn = HouseNumberFactory(parent=street, number="84", ordinal="bis")
    assert hn.cia == '93031_1491_84_BIS'


def test_get_postcode_housenumbers_sorted():
    postcode = PostCodeFactory()
    hn2 = HouseNumberFactory(postcode=postcode, number="2", ordinal="")
    hn2ter = HouseNumberFactory(postcode=postcode, number="2", ordinal="ter")
    hn1 = HouseNumberFactory(postcode=postcode, number="1", ordinal="")
    hn2bis = HouseNumberFactory(postcode=postcode, number="2", ordinal="bis")
    assert postcode.housenumbers == [hn1, hn2, hn2bis, hn2ter]


def test_get_group_housenumbers_parent_sorted():
    group = GroupFactory()
    hn1a = HouseNumberFactory(parent=group, number="1", ordinal="A")
    hn2ter = HouseNumberFactory(parent=group, number="2", ordinal="ter")
    hn1 = HouseNumberFactory(parent=group, number="1", ordinal="")
    hn2bis = HouseNumberFactory(parent=group, number="2", ordinal="bis")
    assert group.housenumbers == [hn1, hn1a, hn2bis, hn2ter]


def test_get_group_housenumbers_ancestor_sorted():
    group = GroupFactory()
    hn1a = HouseNumberFactory(ancestors=group, number="1", ordinal="A")
    hn2ter = HouseNumberFactory(ancestors=group, number="2", ordinal="ter")
    hn1 = HouseNumberFactory(ancestors=group, number="1", ordinal="")
    hn2bis = HouseNumberFactory(ancestors=group, number="2", ordinal="bis")
    assert group.housenumbers == [hn1, hn1a, hn2bis, hn2ter]


def test_get_group_housenumbers_parent_ancestor_sorted():
    group = GroupFactory()
    hn1a = HouseNumberFactory(parent=group, number="1", ordinal="A")
    hn2ter = HouseNumberFactory(parent=group, number="2", ordinal="ter")
    hn1 = HouseNumberFactory(ancestors=group, number="1", ordinal="")
    hn2bis = HouseNumberFactory(ancestors=group, number="2", ordinal="bis")
    assert group.housenumbers == [hn1, hn1a, hn2bis, hn2ter]


def test_cannot_duplicate_housenumber_on_same_street():
    street = GroupFactory()
    HouseNumberFactory(parent=street, ordinal="b", number="10")
    with pytest.raises(peewee.IntegrityError):
        HouseNumberFactory(parent=street, ordinal="b", number="10")


def test_cannot_create_housenumber_without_parent():
    with pytest.raises(peewee.DoesNotExist):
        HouseNumberFactory(parent=None)


def test_housenumber_str():
    hn = HouseNumberFactory(ordinal="b", number="10")
    assert str(hn) == '10 b'


def test_can_create_two_housenumbers_with_same_number_but_different_streets():
    street = GroupFactory()
    street2 = GroupFactory()
    HouseNumberFactory(parent=street, ordinal="b", number="10")
    HouseNumberFactory(parent=street2, ordinal="b", number="10")


def test_housenumber_positions():
    housenumber = HouseNumberFactory()
    position = PositionFactory(housenumber=housenumber)
    assert housenumber.positions == [position.as_relation]


def test_housenumber_positions_without_linked_positions():
    housenumber = HouseNumberFactory()
    assert housenumber.positions == []


def test_create_housenumber_with_district():
    municipality = MunicipalityFactory()
    district = GroupFactory(municipality=municipality, kind=models.Group.AREA)
    housenumber = HouseNumberFactory(ancestors=[district],
                                     street__municipality=municipality)
    assert district in housenumber.ancestors
    assert housenumber in district.housenumbers


def test_add_district_to_housenumber():
    housenumber = HouseNumberFactory()
    district = GroupFactory(municipality=housenumber.parent.municipality,
                            kind=models.Group.AREA)
    housenumber.ancestors.add(district)
    assert district in housenumber.ancestors
    assert housenumber in district.housenumbers


def test_remove_housenumber_ancestors():
    municipality = MunicipalityFactory()
    district = GroupFactory(municipality=municipality, kind=models.Group.AREA)
    housenumber = HouseNumberFactory(ancestors=[district],
                                     street__municipality=municipality)
    assert district in housenumber.ancestors
    housenumber.ancestors.remove(district)
    assert district not in housenumber.ancestors


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


def test_housenumber_as_resource():
    housenumber = HouseNumberFactory(number="90", ordinal="bis",
                                     attributes={"source": "openbar"},
                                     parent__municipality__insee="21892",
                                     parent__fantoir="218921234")
    assert housenumber.as_resource == {
        'ancestors': [],
        'cia': '21892_1234_90_BIS',
        'parent': housenumber.parent.as_relation,
        'positions': [],
        'laposte': None,
        'ign': None,
        'attributes': {'source': 'openbar'},
        'version': 1,
        'id': housenumber.id,
        'number': '90',
        'postcode': None,
        'ordinal': 'bis',
        'created_by': housenumber.created_by.as_relation,
        'created_at': housenumber.created_at,
        'modified_by': housenumber.modified_by.as_relation,
        'modified_at': housenumber.modified_at,
    }


def test_housenumber_as_relation():
    housenumber = HouseNumberFactory(number="90", ordinal="bis",
                                     attributes={"source": "openbar"},
                                     parent__municipality__insee="21892",
                                     parent__fantoir="218921234")
    assert housenumber.as_relation == {
        'cia': '21892_1234_90_BIS',
        'parent': housenumber.parent.id,
        'laposte': None,
        'ign': None,
        'attributes': {'source': 'openbar'},
        'id': housenumber.id,
        'number': '90',
        'postcode': None,
        'ordinal': 'bis',
        'resource': 'housenumber',
        'version': 1,
    }


def test_position_children():
    housenumber = HouseNumberFactory()
    parent = PositionFactory(housenumber=housenumber)
    child = PositionFactory(housenumber=housenumber, parent=parent)
    assert child in parent.children


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
    (None, None),
    ("", None),
])
def test_position_center_coerce(given, expected):
    position = PositionFactory(center=given, name="bâtiment Z")
    center = models.Position.get(models.Position.id == position.id).center
    if given:
        assert center.coords == expected
    else:
        assert not center


def test_cannot_create_position_with_same_housenumber_and_source():
    hn1 = HouseNumberFactory()
    PositionFactory(housenumber=hn1, source="XXX")
    assert models.Position.select().count() == 1
    with pytest.raises(peewee.IntegrityError):
        PositionFactory(housenumber=hn1, source="XXX")
    assert models.Position.select().count() == 1
