import json
from pathlib import Path

from ban.auth import models as amodels
from ban.commands.auth import createuser
from ban.commands.db import truncate
from ban.commands.export import resources
from ban.commands.importer import municipalities
from ban.commands.ignsna import ignsna
from ban.core import models
from ban.core.versioning import Diff
from ban.tests import factories


def test_import_municipalities(staff):
    path = Path(__file__).parent / 'data/municipalities.csv'
    municipalities(path)
    assert len(models.Municipality.select()) == 4
    assert not len(Diff.select())


def test_import_municipalities_can_be_filtered_by_departement(staff):
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


def test_truncate_should_truncate_all_tables_by_default(monkeypatch):
    factories.MunicipalityFactory()
    factories.StreetFactory()
    monkeypatch.setattr('ban.commands.helpers.confirm', lambda *x, **wk: True)
    truncate()
    assert not models.Municipality.select().count()
    assert not models.Street.select().count()


def test_truncate_should_only_truncate_given_names(monkeypatch):
    factories.MunicipalityFactory()
    factories.StreetFactory()
    monkeypatch.setattr('ban.commands.helpers.confirm', lambda *x, **wk: True)
    truncate(names=['street'])
    assert models.Municipality.select().count()
    assert not models.Street.select().count()


def test_truncate_should_not_ask_for_confirm_in_force_mode(monkeypatch):
    factories.MunicipalityFactory()
    truncate(force=True)
    assert not models.Municipality.select().count()


def test_export_resources():
    mun = factories.MunicipalityFactory()
    street = factories.StreetFactory(municipality=mun)
    hn = factories.HouseNumberFactory(street=street)
    factories.PositionFactory(housenumber=hn)
    path = Path(__file__).parent / 'data/export.sjson'
    resources(path)
    with path.open() as f:
        lines = f.readlines()
        assert len(lines) == 3
        assert json.loads(lines[0]) == mun.as_list
        assert json.loads(lines[1]) == street.as_list
        resource = hn.as_list
        # JSON transform internals tuples to lists.
        resource['center']['coordinates'] = list(resource['center']['coordinates'])  # noqa
        assert json.loads(lines[2]) == resource
    path.unlink()


def test_import_ignsna(staff):
    factories.MunicipalityFactory(insee='33236')
    factories.MunicipalityFactory(insee='61403')
    pc_path = Path(__file__).parent / 'data/ignsna/'
    ignsna(str(pc_path))
    post_codes = models.PostCode.select()
    assert len(post_codes) == 1
    assert len(post_codes[0].municipalities) == 2
