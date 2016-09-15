from ..factories import GroupFactory
from .utils import authorize


@authorize
def test_can_flag_current_version(client, url):
    group = GroupFactory()
    version = group.load_version()
    uri = url('group-version-by-sequential', identifier=group.id, ref=1)
    resp = client.post(uri, data={'flag': True})
    assert resp.status_code == 200
    assert version.flags.select().count()


@authorize
def test_can_unflag_current_version(client, url, session):
    group = GroupFactory()
    version = group.load_version()
    version.flag()
    assert version.flags.select().count()
    uri = url('group-version-by-sequential', identifier=group.id, ref=1)
    resp = client.post(uri, data={'flag': False})
    assert resp.status_code == 200
    assert not version.flags.select().count()


@authorize
def test_get_version_contain_flags(client, url, session):
    group = GroupFactory()
    version = group.load_version()
    version.flag()
    uri = url('group-version-by-sequential', identifier=group.id, ref=1)
    resp = client.get(uri)
    assert resp.status_code == 200
    assert 'flags' in resp.json
    assert resp.json['flags'][0]['by'] == 'laposte'


@authorize
def test_can_flag_past_version(client, url):
    group = GroupFactory()
    group.name = 'Another name'
    group.increment_version()
    group.save()
    uri = url('group-version-by-sequential', identifier=group.id, ref=1)
    resp = client.post(uri, data={'flag': True})
    assert resp.status_code == 200
    version = group.load_version(1)
    assert version.flags.select().count()
    version = group.load_version(2)
    assert not version.flags.select().count()


def test_cannot_flag_without_token(client, url):
    group = GroupFactory()
    uri = url('group-version-by-sequential', identifier=group.id, ref=1)
    resp = client.post(uri, data={'flag': True})
    assert resp.status_code == 401
