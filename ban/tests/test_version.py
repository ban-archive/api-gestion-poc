import peewee
import pytest

from ban.core import models
from ban.core.versioning import Version

from .factories import (GroupFactory, HouseNumberFactory, MunicipalityFactory,
                        PositionFactory, PostCodeFactory)


def test_municipality_version():
    municipality = MunicipalityFactory(insee='12345', name='Lille',
                                       siren='123456789', alias=['Rijsel'],
                                       attributes={'key': 'value'})
    PostCodeFactory(municipality=municipality)
    assert municipality.as_version == {
        'siren': '123456789',
        'modified_by': municipality.modified_by.serialize(),
        'attributes': {'key': 'value'},
        'id': municipality.id,
        'name': 'Lille',
        'insee': '12345',
        'created_at': municipality.created_at.isoformat(),
        'alias': ['Rijsel'],
        'created_by': municipality.created_by.serialize(),
        'modified_at': municipality.modified_at.isoformat(),
        'version': 1}


def test_municipality_is_versioned():
    municipality = MunicipalityFactory(name='Moret-sur-Loing')
    assert len(municipality.versions) == 1
    assert municipality.version == 1
    municipality.name = 'Orvanne'
    municipality.increment_version()
    municipality.save()
    assert municipality.version == 2
    versions = municipality.versions
    assert len(versions) == 2
    version1 = versions[0].load()
    version2 = versions[1].load()
    assert versions[0].period.upper == versions[1].period.lower
    assert versions[1].period.upper is None
    assert version1.name == 'Moret-sur-Loing'
    assert version2.name == 'Orvanne'
    municipality.insee = '77316'
    municipality.increment_version()
    municipality.save()
    versions = municipality.versions
    assert len(versions) == 3
    assert versions[0].period.upper == versions[1].period.lower
    assert versions[1].period.upper == versions[2].period.lower
    assert versions[2].period.upper is None


def test_save_should_be_rollbacked_if_version_save_fails():
    municipality = MunicipalityFactory()
    assert Version.select().count() == 1
    # Artificially create a version
    municipality.increment_version()
    municipality.store_version()
    assert Version.select().count() == 2
    with pytest.raises(peewee.IntegrityError):
        municipality.save()
    assert Version.select().count() == 2
    models.Municipality.select().count() == 1


def test_group_is_versioned():
    initial_name = "Rue des Pommes"
    street = GroupFactory(name=initial_name)
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


def test_group_version():
    group = GroupFactory(name="Rue de la Princesse Lila", fantoir="123456789",
                         attributes={'key': 'value'}, laposte='123456',
                         alias=['Rue du Prince Louison'],
                         addressing=models.Group.ANARCHICAL)
    assert group.as_version == {
        'kind': 'way',
        'municipality': group.municipality.id,
        'addressing': 'anarchical',
        'fantoir': '123456789',
        'modified_by': group.modified_by.serialize(),
        'attributes': {'key': 'value'},
        'id': group.id,
        'laposte': '123456',
        'ign': None,
        'name': 'Rue de la Princesse Lila',
        'created_at': group.created_at.isoformat(),
        'alias': ['Rue du Prince Louison'],
        'created_by': group.created_by.serialize(),
        'modified_at': group.modified_at.isoformat(),
        'version': 1}


def test_housenumber_is_versioned():
    street = GroupFactory()
    hn = HouseNumberFactory(parent=street, ordinal="b")
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
    assert version2.parent == street


def test_housenumber_as_version():
    postcode = PostCodeFactory()
    street = GroupFactory(fantoir='123456789', municipality__insee='12345')
    district = GroupFactory()
    hn = HouseNumberFactory(number="84", ordinal="bis", postcode=postcode,
                            ancestors=[district], parent=street,
                            laposte='123456')
    assert hn.as_version == {
        'laposte': '123456',
        'cia': '12345_6789_84_BIS',
        'version': 1,
        'ordinal': 'bis',
        'number': '84',
        'id': hn.id,
        'created_by': hn.created_by.serialize(),
        'ancestors': [district.id],
        'postcode': postcode.id,
        'modified_at': hn.modified_at.isoformat(),
        'ign': None,
        'created_at': hn.created_at.isoformat(),
        'parent': street.id,
        'modified_by': hn.modified_by.serialize(),
        'positions': [],
        'attributes': None}


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
    assert version1.center.geojson == {'type': 'Point', 'coordinates': (1, 2)}
    assert version2.center.geojson == {'type': 'Point', 'coordinates': (3, 4)}
    assert version2.housenumber == housenumber


def test_position_as_version():
    parent = PositionFactory()
    position = PositionFactory(ign='123456', attributes={'key': 'value'},
                               name='Bâtiment A', parent=parent,
                               housenumber=parent.housenumber)
    assert position.as_version == {
        'created_by': position.created_by.serialize(),
        'housenumber': position.housenumber.id,
        'modified_by': position.modified_by.serialize(),
        'attributes': {'key': 'value'},
        'created_at': position.created_at.isoformat(),
        'modified_at': position.modified_at.isoformat(),
        'source': None,
        'parent': parent.id,
        'positioning': 'imagery',
        'name': 'Bâtiment A',
        'ign': '123456',
        'kind': 'entrance',
        'version': 1,
        'center': {'coordinates': (-1.1111, 48.8888), 'type': 'Point'},
        'comment': None,
        'id': position.id}
