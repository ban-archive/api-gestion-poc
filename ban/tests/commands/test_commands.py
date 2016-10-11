import json
from pathlib import Path

from ban.auth import models as amodels
from ban.commands.auth import createuser, listusers, createclient, listclients
from ban.commands.db import truncate
from ban.commands.export import resources
from ban.commands.importer import municipalities
from ban.core import models
from ban.core.encoder import dumps
from ban.core.versioning import Diff
from ban.tests import factories


def test_import_municipalities(staff, config):
    path = Path(__file__).parent / 'data/municipalities.csv'
    municipalities(path)
    assert len(models.Municipality.select()) == 4
    assert not len(Diff.select())


def test_import_municipalities_can_be_filtered_by_departement(staff, config):
    path = Path(__file__).parent / 'data/municipalities.csv'
    municipalities(path, departement=33)
    assert len(models.Municipality.select()) == 1
    assert not len(Diff.select())


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


def test_create_client_should_accept_username():
    user = factories.UserFactory()
    assert not amodels.Client.select().count()
    createclient(name='test client', user=user.username)
    assert amodels.Client.select().count() == 1
    client = amodels.Client.first()
    assert client.user == user


def test_create_client_should_accept_email():
    user = factories.UserFactory()
    assert not amodels.Client.select().count()
    createclient(name='test client', user=user.email)
    assert amodels.Client.select().count() == 1
    client = amodels.Client.first()
    assert client.user == user


def test_create_client_should_not_crash_on_non_existing_user(capsys):
    assert not amodels.Client.select().count()
    createclient(name='test client', user='doesnotexist')
    assert not amodels.Client.select().count()
    out, err = capsys.readouterr()
    assert 'User not found' in out


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


def test_export_resources():
    mun = factories.MunicipalityFactory()
    street = factories.GroupFactory(municipality=mun)
    hn = factories.HouseNumberFactory(parent=street)
    factories.PositionFactory(housenumber=hn)
    path = Path(__file__).parent / 'data/export.sjson'
    resources(path)

    with path.open() as f:
        lines = f.readlines()
        assert len(lines) == 3
        # loads/dumps to compare string dates to string dates.
        assert json.loads(lines[0]) == json.loads(dumps(mun.as_resource))
        assert json.loads(lines[1]) == json.loads(dumps(street.as_resource))
        # Plus, JSON transform internals tuples to lists.
        assert json.loads(lines[2]) == json.loads(dumps(hn.as_resource))
    path.unlink()
