from ..factories import GroupFactory
from .utils import authorize


@authorize
def test_can_flag_current_version(client):
    group = GroupFactory()
    version = group.load_version()
    uri = '/group/{}/versions/1/flag'.format(group.id)
    resp = client.post(uri, data={'status': True})
    assert resp.status_code == 200
    assert version.flags.select().count()


@authorize
def test_can_unflag_current_version(client, session):
    group = GroupFactory()
    version = group.load_version()
    uri = '/group/{}/versions/1/flag'.format(group.id)
    resp = client.post(uri, data={'status': True})
    assert resp.status_code == 200
    assert version.flags.select().count()


@authorize
def test_get_version_contain_flags(client, session):
    group = GroupFactory()
    version = group.load_version()
    version.flag()
    uri = '/group/{}/versions/1'.format(group.id)
    resp = client.get(uri)
    assert resp.status_code == 200
    assert 'flags' in resp.json
    assert resp.json['flags'][0]['by'] == 'laposte'


@authorize
def test_can_flag_past_version(client):
    group = GroupFactory()
    group.name = 'Another name'
    group.increment_version()
    group.save()
    uri = '/group/{}/versions/1/flag'.format(group.id)
    resp = client.post(uri, data={'status': True})
    assert resp.status_code == 200
    version = group.load_version(1)
    assert version.flags.select().count()
    version = group.load_version(2)
    assert not version.flags.select().count()


@authorize
def test_invalid_reference_returns_404(client):
    group = GroupFactory()
    group.name = 'Another name'
    group.increment_version()
    group.save()
    uri = '/group/{}/versions/9/flag'.format(group.id)
    resp = client.post(uri, data={'status': True})
    assert resp.status_code == 404
    assert resp.json['error'] == 'Version reference `9` not found'


def test_cannot_flag_without_token(client):
    group = GroupFactory()
    uri = '/group/{}/versions/1/flag'.format(group.id)
    resp = client.post(uri, data={'status': True})
    assert resp.status_code == 401
