import peewee
import pytest

from ban.core.versioning import Redirect

from . import factories


def test_resource_create_does_not_create_redirect():
    factories.PositionFactory()
    assert not Redirect.select().count()


def test_resource_update_does_not_create_redirect_if_no_identifier_changed():
    municipality = factories.MunicipalityFactory(insee="12345")
    municipality.name = 'Another Name'
    municipality.increment_version()
    municipality.save()
    assert not Redirect.select().count()


def test_resource_update_creates_redirect_if_some_identifier_changed():
    municipality = factories.MunicipalityFactory(insee="12345")
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    assert Redirect.select().count() == 1
    redirect = Redirect.first()
    assert redirect.model_name == 'municipality'
    assert redirect.identifier == 'insee'
    assert redirect.value == '12345'
    assert redirect.model_id == municipality.id


def test_follow_returns_new_value():
    municipality = factories.MunicipalityFactory(insee="12345")
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    assert Redirect.select().count() == 1
    assert Redirect.follow('municipality', 'insee', '12345') == [
        municipality.id]


def test_resource_update_should_propagate_if_target_is_becomming_source():
    municipality = factories.MunicipalityFactory(insee='12345')
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    assert Redirect.select().count() == 1
    assert Redirect.follow('municipality', 'insee', '12345') == [
        municipality.id]
    municipality2 = factories.MunicipalityFactory(insee='12321')
    # Should also update '12345'
    Redirect.add(municipality2, 'insee', '54321')
    municipality.delete_instance()
    assert Redirect.select().count() == 2
    assert Redirect.follow('municipality', 'insee', '54321') == [
        municipality2.id]
    assert Redirect.follow('municipality', 'insee', '12345') == [
        municipality2.id]


def test_can_add_a_redirect():
    position = factories.PositionFactory()
    Redirect.add(position, 'pk', '939')
    assert Redirect.select().count() == 1
    assert Redirect.follow('Position', 'pk', '939') == [
        position.id]


def test_cannot_create_redirect_with_invalid_identifier():
    position = factories.PositionFactory()
    with pytest.raises(ValueError):
        Redirect.add(position, 'invalid', '939')
    assert not Redirect.select().count()


def test_cannot_create_cyclic_redirect():
    position = factories.PositionFactory(ign='123456789')
    with pytest.raises(ValueError):
        Redirect.add(position, 'ign', '123456789')
    assert not Redirect.select().count()


def test_can_remove_a_redirect():
    position = factories.PositionFactory()
    Redirect.add(position, 'pk', 32)
    assert Redirect.select().count() == 1
    Redirect.remove(position, 'pk', 32)
    assert not Redirect.select().count()


def test_can_point_from_an_identifier_to_another():
    municipality = factories.MunicipalityFactory()
    Redirect.add(municipality, 'insee', '12345')
    assert Redirect.select().count() == 1
    assert Redirect.follow('municipality', 'insee', '12345') == [
        municipality.id]


def test_can_create_multiple_redirections():
    position1 = factories.PositionFactory()
    position2 = factories.PositionFactory()
    Redirect.add(position1, 'pk', '939')
    assert Redirect.select().count() == 1
    Redirect.add(position2, 'pk', '939')
    assert Redirect.select().count() == 2
    redirects = Redirect.follow('Position', 'pk', '939')
    assert position1.id in redirects
    assert position2.id in redirects


def test_cannot_duplicate_redirection():
    position = factories.PositionFactory()
    Redirect.add(position, 'pk', '939')
    assert Redirect.select().count() == 1
    Redirect.add(position, 'pk', '939')
    assert Redirect.select().count() == 1
    assert Redirect.follow('Position', 'pk', '939') == [position.id]


def test_deleting_resource_should_remove_redirects_pointing_to_it():
    position = factories.PositionFactory()
    Redirect.add(position, 'pk', 32)
    assert Redirect.select().count() == 1
    position.delete_instance()
    assert not Redirect.select().count()


def test_should_not_be_deleted_if_instance_remove_fails():
    housenumber = factories.HouseNumberFactory()
    position = factories.PositionFactory(housenumber=housenumber)
    Redirect.add(position, 'pk', 32)
    assert Redirect.select().count() == 1
    with pytest.raises(peewee.IntegrityError):
        housenumber.delete_instance()
    assert Redirect.select().count() == 1
