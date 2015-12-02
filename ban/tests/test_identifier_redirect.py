from ban.core.versioning import IdentifierRedirect
from ban.core import models

from . import factories


def test_resource_create_does_not_create_redirect():
    factories.PositionFactory()
    assert not IdentifierRedirect.select().count()


def test_resource_update_does_not_create_redirect_if_no_identifier_changed():
    municipality = factories.MunicipalityFactory(insee="12345")
    municipality.name = 'Another Name'
    municipality.increment_version()
    municipality.save()
    assert not IdentifierRedirect.select().count()


def test_resource_update_creates_redirect_if_some_identifier_changed():
    municipality = factories.MunicipalityFactory(insee="12345")
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    assert IdentifierRedirect.select().count() == 1
    redirect = IdentifierRedirect.first()
    assert redirect.model_name == 'Municipality'
    assert redirect.identifier == 'insee'
    assert redirect.old == '12345'
    assert redirect.new == '54321'


def test_follow_returns_new_value():
    municipality = factories.MunicipalityFactory(insee="12345")
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    assert IdentifierRedirect.select().count() == 1
    assert IdentifierRedirect.follow(models.Municipality, 'insee', '12345') == '54321'  # noqa


def test_resource_update_should_refresh_if_target_is_becomming_source():
    municipality = factories.MunicipalityFactory(insee="12345")
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    assert IdentifierRedirect.select().count() == 1
    municipality.insee = '12321'
    municipality.increment_version()
    municipality.save()
    assert IdentifierRedirect.select().count() == 2
    assert IdentifierRedirect.follow(models.Municipality, 'insee', '54321') == '12321'  # noqa
    assert IdentifierRedirect.follow(models.Municipality, 'insee', '12345') == '12321'  # noqa
