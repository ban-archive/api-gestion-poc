from .factories import MunicipalityFactory


def test_only_changed_columns_should_be_in_diff():
    municipality = MunicipalityFactory(name='Moret-sur-Loing', insee='77316',
                                       siren='987654321')
    municipality.name = 'Orvanne'
    municipality.siren = '123456789'
    # "Changed" with same value.
    municipality.insee = '77316'
    municipality.increment_version()
    municipality.save()
    diff = municipality.versions[1].diff
    assert len(diff.diff) == 2  # name, siren
    assert diff.diff['name']['old'] == 'Moret-sur-Loing'
    assert diff.diff['name']['new'] == 'Orvanne'
    assert diff.diff['siren']['old'] == '987654321'
    assert diff.diff['siren']['new'] == '123456789'
    municipality.insee = '77319'
    municipality.increment_version()
    municipality.save()
    diff = municipality.versions[2].diff
    assert len(diff.diff) == 1  # insee
    assert diff.diff['insee']['old'] == '77316'
    assert diff.diff['insee']['new'] == '77319'


def test_adding_value_to_arrayfield_column():
    municipality = MunicipalityFactory(name='Moret-sur-Loing')
    municipality.alias = ['Orvanne']
    municipality.increment_version()
    municipality.save()
    diff = municipality.versions[1].diff
    assert len(diff.diff) == 1  # name, siren
    assert diff.diff['alias']['old'] is None
    assert diff.diff['alias']['new'] == ['Orvanne']


def test_delete_should_create_a_diff():
    municipality = MunicipalityFactory()
    municipality.mark_deleted()
    diff = municipality.versions[1].diff
    assert len(diff.diff) == 1  # name, siren
    assert diff.diff['status']['old'] == 'active'
    assert diff.diff['status']['new'] == 'deleted'
