from .factories import GroupFactory, HouseNumberFactory


def test_simple_serialize():
    group = GroupFactory(name='Rue de la Banatouille', kind='way')
    assert group.serialize({'name': {}, 'kind': {}}) == {
        'name': 'Rue de la Banatouille',
        'kind': 'way',
    }


def test_serialize_relation_reference():
    group = GroupFactory(name='Rue de la Banatouille')
    assert group.serialize({'name': {}, 'municipality': {}}) == {
        'name': 'Rue de la Banatouille',
        'municipality': group.municipality.id
    }


def test_serialize_relation_with_subfields():
    group = GroupFactory(name='Rue de la Banatouille',
                         municipality__name='Epine')
    assert group.serialize({'name': {}, 'municipality': {'name': {}}}) == {
        'name': 'Rue de la Banatouille',
        'municipality': {
            'name': 'Epine'
        }
    }


def test_serialize_with_wildcard():
    group = GroupFactory(name='Rue de la Banatouille', fantoir='930311491',
                         municipality__name='Epine')
    assert group.serialize({'*': {}}) == {
        'name': 'Rue de la Banatouille',
        'id': group.id,
        'municipality': group.municipality.id,
        'kind': 'way',
        'fantoir': '930311491',
        'alias': None,
        'ign': None,
        'name': 'Rue de la Banatouille',
        'attributes': None,
        'laposte': None,
        'addressing': None,
        'version': 1,
        'modified_at': group.modified_at.isoformat(),
        'created_at': group.created_at.isoformat(),
        'created_by': {
            'client': group.created_by.client.name,
            'user': group.created_by.user.username,
            'id': group.created_by.pk,
        },
        'modified_by': {
            'client': group.modified_by.client.name,
            'user': group.modified_by.user.username,
            'id': group.modified_by.pk,
        },
    }


def test_serialize_with_wildcard_in_relation():
    group = GroupFactory(name='Rue de la Banatouille', fantoir='930311491')
    housenumber = HouseNumberFactory(parent=group)
    assert housenumber.serialize({'parent': {'*': {}}}) == {
        'parent': {
            'name': 'Rue de la Banatouille',
            'id': group.id,
            'municipality': group.municipality.id,
            'kind': 'way',
            'fantoir': '930311491',
            'alias': None,
            'ign': None,
            'name': 'Rue de la Banatouille',
            'attributes': None,
            'laposte': None,
            'addressing': None,
            'version': 1,
            'modified_at': group.modified_at.isoformat(),
            'created_at': group.created_at.isoformat(),
            'created_by': {
                'client': group.created_by.client.name,
                'user': group.created_by.user.username,
                'id': group.created_by.pk,
            },
            'modified_by': {
                'client': group.modified_by.client.name,
                'user': group.modified_by.user.username,
                'id': group.modified_by.pk,
            },
        }
    }


def test_serialize_with_double_wildcard():
    group = GroupFactory(name='Rue de la Banatouille', fantoir='930311491',
                         municipality__insee='93031')
    housenumber = HouseNumberFactory(parent=group, number='1', ordinal='bis')
    assert housenumber.serialize({'*': {'*': {}}}) == {
        'id': housenumber.id,
        'number': '1',
        'ordinal': 'bis',
        'modified_at': housenumber.modified_at.isoformat(),
        'created_at': housenumber.created_at.isoformat(),
        'created_by': {
            'client': housenumber.created_by.client.name,
            'user': housenumber.created_by.user.username,
            'id': housenumber.created_by.pk,
        },
        'modified_by': {
            'client': housenumber.modified_by.client.name,
            'user': housenumber.modified_by.user.username,
            'id': housenumber.modified_by.pk,
        },
        'version': 1,
        'postcode': None,
        'ancestors': [],
        'laposte': None,
        'cia': '93031_1491_1_BIS',
        'ign': None,
        'attributes': None,
        'positions': [],
        'parent': {
            'name': 'Rue de la Banatouille',
            'id': group.id,
            'municipality': group.municipality.id,
            'kind': 'way',
            'fantoir': '930311491',
            'alias': None,
            'ign': None,
            'name': 'Rue de la Banatouille',
            'attributes': None,
            'laposte': None,
            'addressing': None,
            'version': 1,
            'modified_at': group.modified_at.isoformat(),
            'created_at': group.created_at.isoformat(),
            'created_by': {
                'client': group.created_by.client.name,
                'user': group.created_by.user.username,
                'id': group.created_by.pk,
            },
            'modified_by': {
                'client': group.modified_by.client.name,
                'user': group.modified_by.user.username,
                'id': group.modified_by.pk,
            },
        }
    }


def test_serialize_manytomany():
    group = GroupFactory(name='Rue de la Banatouille', fantoir='930311491')
    housenumber = HouseNumberFactory(ancestors=[group])
    assert housenumber.serialize({'ancestors': {'name': {}, 'id': {}}}) == {
        'ancestors': [{
            'name': 'Rue de la Banatouille',
            'id': group.id,
        }]
    }
