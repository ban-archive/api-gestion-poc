from pathlib import Path

from ban.commands.importer import municipalities
from ban.commands.auth import createuser
from ban.core import models
from ban.core.versioning import Diff
from ban.auth import models as amodels


def test_import_municipalities(staff, monkeypatch):
    path = Path(__file__).parent / 'data/municipalities.csv'
    municipalities(path)
    assert len(models.Municipality.select()) == 4
    assert not len(Diff.select())


def test_import_municipalities_can_be_filtered_by_departement(staff):
    path = Path(__file__).parent / 'data/municipalities.csv'
    municipalities(path, departement=33)
    assert len(models.Municipality.select()) == 1
    assert not len(Diff.select())


def test_create_user(monkeypatch):
    monkeypatch.setattr('ban.commands.helpers.prompt', lambda *x, **wk: 'pwd')
    assert not amodels.User.select().count()
    createuser(username='testuser', email='aaaa@bbbb.org')
    assert amodels.User.select().count() == 1
    user = amodels.User.first()
    assert user.is_staff
