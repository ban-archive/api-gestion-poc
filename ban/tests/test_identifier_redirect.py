from ban.core.versioning import IdentifierRedirect

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
    assert redirect.from_identifier == 'insee'
    assert redirect.to_identifier == 'insee'
    assert redirect.from_value == '12345'
    assert redirect.to_value == '54321'


def test_follow_returns_new_value():
    municipality = factories.MunicipalityFactory(insee="12345")
    municipality.insee = '54321'
    municipality.increment_version()
    municipality.save()
    assert IdentifierRedirect.select().count() == 1
    assert IdentifierRedirect.follow('Municipality', 'insee', '12345') == [
        ('insee', '54321')]


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
    assert IdentifierRedirect.follow('Municipality', 'insee', '54321') == [
        ('insee', '12321')]
    assert IdentifierRedirect.follow('Municipality', 'insee', '12345') == [
        ('insee', '12321')]


def test_can_add_a_redirect():
    position = factories.PositionFactory()
    pk = position.pk
    IdentifierRedirect.add('Position', 'pk', '939', 'pk', pk)
    assert IdentifierRedirect.select().count() == 1
    assert IdentifierRedirect.follow('Position', 'pk', '939') == [
        ('pk', str(pk))]


def test_can_remove_a_redirect():
    position = factories.PositionFactory()
    IdentifierRedirect.add('Position', 'pk', 32, 'pk', position.pk)
    assert IdentifierRedirect.select().count() == 1
    IdentifierRedirect.remove('Position', 'pk', 32, 'pk', position.pk)
    assert not IdentifierRedirect.select().count()


def test_can_point_from_an_identifier_to_another():
    IdentifierRedirect.add('Municipality', 'insee', '12345', 'pk', '12')
    assert IdentifierRedirect.select().count() == 1
    assert IdentifierRedirect.follow('Municipality', 'insee', '12345') == [
        ('pk', '12')]


def test_can_create_multiple_redirections():
    IdentifierRedirect.add('Position', 'pk', '939', 'pk', '123')
    assert IdentifierRedirect.select().count() == 1
    IdentifierRedirect.add('Position', 'pk', '939', 'pk', '456')
    assert IdentifierRedirect.select().count() == 2
    assert IdentifierRedirect.follow('Position', 'pk', '939') == [
        ('pk', '123'), ('pk', '456')]


def test_cannot_duplicate_redirection():
    IdentifierRedirect.add('Position', 'pk', '939', 'pk', '123')
    assert IdentifierRedirect.select().count() == 1
    IdentifierRedirect.add('Position', 'pk', '939', 'pk', '123')
    assert IdentifierRedirect.select().count() == 1
    assert IdentifierRedirect.follow('Position', 'pk', '939') == [
        ('pk', '123')]
