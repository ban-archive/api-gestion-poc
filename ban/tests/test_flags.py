import pytest

from ban.core import context

from .factories import GroupFactory, SessionFactory
from ban.auth import models as auth_models


def test_can_flag_current_version(session):
    group = GroupFactory()
    version = group.load_version()
    version.flag()
    assert version.flags.select().count()


def test_cannot_duplicate_flag(session):
    group = GroupFactory()
    version = group.load_version()
    version.flag()
    version.flag()
    assert version.flags.select().count() == 1


def test_can_flag_past_version(session):
    group = GroupFactory()
    group.name = 'Another name'
    group.increment_version()
    group.save()
    version = group.load_version(1)
    version.flag()
    assert version.flags.select().count()
    version = group.load_version(2)
    assert not version.flags.select().count()


def test_can_unflag_current_version(session):
    group = GroupFactory()
    version = group.load_version()
    version.flag()
    assert version.flags.select().count()
    version.unflag()
    assert not version.flags.select().count()


def test_cannot_unflag_other_client_flag(session):
    group = GroupFactory()
    version = group.load_version()
    version.flag()
    # Change current session
    session = SessionFactory()
    context.set('session', session)
    assert version.flags.select().count() == 1
    version.unflag()
    assert version.flags.select().count() == 1


def test_cannot_flag_without_session():
    group = GroupFactory()
    with pytest.raises(ValueError):
        group.load_version().flag()


def test_cannot_flag_if_session_has_no_client(session):
    group = GroupFactory()
    session.client = None
    with pytest.raises(ValueError):
        group.load_version().flag()


def test_cannot_flag_if_session_has_no_contributor_type(session):
    group = GroupFactory()
    session.contributor_type = None
    with pytest.raises(ValueError):
        group.load_version().flag()


def test_cannot_flag_with_contributor_type_viewer(session):
    group = GroupFactory()
    session.contributor_type = auth_models.Client.TYPE_VIEWER
    with pytest.raises(ValueError):
        group.load_version().flag()


def test_version_flags_attribute_returns_flags(session):
    group = GroupFactory()
    group.load_version().flag()
    version = group.load_version()
    assert version.flags.count()
    flag = version.flags[0]
    assert flag.created_at
