import json
from unittest.mock import Mock
from pathlib import Path

from ban.auth import models as amodels
from ban.commands.auth import (createclient, createuser, dummytoken,
                               listclients, listusers, invalidatetoken)
from ban.commands.db import truncate
from ban.commands.export import resources
from ban.core import models
from ban.core.encoder import dumps
from ban.tests import factories
from ban.utils import utcnow


def test_create_user_is_not_staff_by_default(monkeypatch):
    monkeypatch.setattr('ban.commands.helpers.prompt', lambda *x, **wk: 'pwd')
    assert not amodels.User.select().count()
    createuser(username='testuser', email='aaaa@bbbb.org')
    assert amodels.User.select().count() == 1
    user = amodels.User.first()
    assert not user.is_staff


def test_create_user_should_accept_is_staff_kwarg(monkeypatch):
    monkeypatch.setattr('ban.commands.helpers.prompt', lambda *x, **wk: 'pwd')
    assert not amodels.User.select().count()
    createuser(username='testuser', email='aaaa@bbbb.org', is_staff=True)
    assert amodels.User.select().count() == 1
    user = amodels.User.first()
    assert user.is_staff


def test_listusers(capsys):
    user = factories.UserFactory()
    listusers()
    out, err = capsys.readouterr()
    assert user.username in out


def test_listusers_with_invoke(capsys):
    user = factories.UserFactory()
    listusers.invoke([])
    out, err = capsys.readouterr()
    assert user.username in out


def test_create_client_should_accept_username():
    user = factories.UserFactory()
    assert not amodels.Client.select().count()
    createclient(name='test client', user=user.username, scopes=['test'])
    assert amodels.Client.select().count() == 1
    client = amodels.Client.first()
    assert client.user == user


def test_create_client_should_accept_email():
    user = factories.UserFactory()
    assert not amodels.Client.select().count()
    createclient(name='test client', user=user.email, scopes=['test'])
    assert amodels.Client.select().count() == 1
    client = amodels.Client.first()
    assert client.user == user


def test_create_client_should_not_crash_on_non_existing_user(capsys):
    assert not amodels.Client.select().count()
    createclient(name='test client', user='doesnotexist')
    assert not amodels.Client.select().count()
    out, err = capsys.readouterr()
    assert 'User not found' in out


def test_create_client_with_scopes(monkeypatch):
    monkeypatch.setattr('ban.commands.helpers.prompt',
                        lambda *x, **wk: 'municipality_write group_write')
    user = factories.UserFactory()
    createclient(name='test client', user=user.username)
    client = amodels.Client.first()
    assert client.scopes == ['municipality_write', 'group_write']


def test_create_client_without_scopes(monkeypatch):
    monkeypatch.setattr('ban.commands.helpers.prompt', lambda *x, **wk: '')
    user = factories.UserFactory()
    createclient(name='test client', user=user.username)
    client = amodels.Client.first()
    assert client.scopes == []


def test_listclients(capsys):
    client = factories.ClientFactory()
    listclients()
    out, err = capsys.readouterr()
    assert client.name in out
    assert str(client.client_id) in out
    assert client.client_secret in out


def test_truncate_should_truncate_all_tables_by_default(monkeypatch):
    factories.MunicipalityFactory()
    factories.GroupFactory()
    monkeypatch.setattr('ban.commands.helpers.confirm', lambda *x, **wk: True)
    truncate()
    assert not models.Municipality.select().count()
    assert not models.Group.select().count()


def test_truncate_should_only_truncate_given_names(monkeypatch):
    factories.MunicipalityFactory()
    factories.GroupFactory()
    monkeypatch.setattr('ban.commands.helpers.confirm', lambda *x, **wk: True)
    truncate('group')
    assert models.Municipality.select().count()
    assert not models.Group.select().count()


def test_truncate_should_not_ask_for_confirm_in_force_mode(monkeypatch):
    factories.MunicipalityFactory()
    truncate(force=True)
    assert not models.Municipality.select().count()


def test_export_municipality():
    mun = factories.MunicipalityFactory()
    path = Path(__file__).parent / 'data'
    resources('Municipality', path)

    filepath = path.joinpath('municipality.ndjson')
    with filepath.open() as f:
        lines = f.readlines()
        assert len(lines) == 1
        # loads/dumps to compare string dates to string dates.
        assert json.loads(lines[0]) == json.loads(dumps(mun.as_export))
    filepath.unlink()


def test_export_group():
    street = factories.GroupFactory()
    path = Path(__file__).parent / 'data'
    resources('Group', path)

    filepath = path.joinpath('group.ndjson')
    with filepath.open() as f:
        lines = f.readlines()
        assert len(lines) == 1
        # loads/dumps to compare string dates to string dates.
        assert json.loads(lines[0]) == json.loads(dumps(street.as_export))
    filepath.unlink()


def test_export_housenumber():
    hn = factories.HouseNumberFactory(number='1')
    hn2 = factories.HouseNumberFactory(number='2')
    path = Path(__file__).parent / 'data'
    resources('HouseNumber', path)

    filepath = path.joinpath('housenumber.ndjson')
    with filepath.open() as f:
        lines = f.readlines()
        assert len(lines) == 2
        # Plus, JSON transform internals tuples to lists.
        assert json.loads(lines[0]) == json.loads(dumps(hn.as_export))
        assert json.loads(lines[1]) == json.loads(dumps(hn2.as_export))
    filepath.unlink()


def test_export_position():
    position = factories.PositionFactory()
    deleted = factories.PositionFactory()
    deleted.mark_deleted()
    path = Path(__file__).parent / 'data'
    resources('Position', path)

    filepath = path.joinpath('position.ndjson')
    with filepath.open() as f:
        lines = f.readlines()
        assert len(lines) == 1
        # Plus, JSON transform internals tuples to lists.
        assert json.loads(lines[0]) == json.loads(dumps(position.as_export))
    filepath.unlink()


def test_export_postcode():
    pc = factories.PostCodeFactory()
    path = Path(__file__).parent / 'data'
    resources('PostCode', path)

    filepath = path.joinpath('position.ndjson')
    with filepath.open() as f:
        lines = f.readlines()
        assert len(lines) == 1
        # Plus, JSON transform internals tuples to lists.
        assert json.loads(lines[0]) == json.loads(dumps(pc.as_export))
    filepath.unlink()


def test_cannot_export_wrong_resource():
    pc = factories.PostCodeFactory()
    path = Path(__file__).parent / 'data'
    with pytest.raises(SystemExit):
        resources('toto', path)


def test_dummytoken():
    factories.UserFactory(is_staff=True)
    token = 'tokenname'
    args = Mock(spec='token')
    args.token = token
    dummytoken.invoke(args)
    assert amodels.Token.select().where(amodels.Token.access_token == token)


def test_report_to(tmpdir, config):
    report_to = tmpdir.join('report')
    config.REPORT_TO = str(report_to)
    factories.UserFactory(is_staff=True)
    token = 'tokenname'
    args = Mock(spec='token')
    args.token = token
    dummytoken.invoke(args)
    with report_to.open() as f:
        assert 'Created token' in f.read()


def test_invalidate_token_with_user(capsys):
    user = factories.UserFactory()
    session = factories.SessionFactory(user=user)
    token = factories.TokenFactory(session=session)
    invalidatetoken(user=user.email)

    out, err = capsys.readouterr()
    assert 'Invalidate 1 token' in out
    updated_token = amodels.Token.first(amodels.Token.pk == token.pk)
    assert updated_token.is_expired


def test_invalidate_token_with_client(capsys):
    client = factories.ClientFactory()
    session = factories.SessionFactory(client=client)
    valid_client = factories.ClientFactory()
    valid_session = factories.SessionFactory(client=valid_client)
    token = factories.TokenFactory(session=session)
    valid_token = factories.TokenFactory(session=valid_session)
    invalidatetoken(client=client.client_id)

    out, err = capsys.readouterr()
    assert 'Invalidate 1 token' in out
    updated_token = amodels.Token.first(amodels.Token.pk == token.pk)
    updated_valid_token = amodels.Token.first(
        amodels.Token.pk == valid_token.pk
    )
    assert utcnow().date() >= updated_token.expires.date()
    assert updated_token.is_expired
    assert updated_valid_token.is_valid()
