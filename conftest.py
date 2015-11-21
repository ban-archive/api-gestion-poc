import pytest

from ban.tests.factories import UserFactory, TokenFactory, SessionFactory

from ban import db
from ban.commands.db import models, create as createdb, truncate as truncatedb
from ban.core import context
from ban.http import application


def pytest_configure(config):
    assert db.test.database.startswith('test_')
    db.test.connect()
    for model in models:
        model._meta.database = db.test
    createdb(fail_silently=True)
    verbose = config.getoption('verbose')
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


def pytest_unconfigure(config):
    db.test.drop_tables(models)
    db.test.close()


def pytest_runtest_setup(item):
    truncatedb(force=True)
    context.set('session', None)


@pytest.fixture()
def user():
    return UserFactory()


@pytest.fixture()
def staff():
    return UserFactory(is_staff=True)


@pytest.fixture()
def session():
    session = SessionFactory()
    context.set('session', session)
    return session


@pytest.fixture()
def token():
    return TokenFactory()


@pytest.fixture
def app():
    return application


@pytest.fixture
def get(client):
    return client.get


@pytest.fixture()
def url():
    def _(klass, **kwargs):
        url = None
        if 'identifier' in kwargs:
            kwargs['id'] = '{identifier}:{id}'.format(**kwargs)
        for route in klass.routes()[::-1]:
            try:
                url = route.format(**kwargs)
            except KeyError:
                continue
            else:
                break
        return url
    return _


class MonkeyPatchWrapper(object):
    def __init__(self, monkeypatch, wrapped_object):
        super().__setattr__('monkeypatch', monkeypatch)
        super().__setattr__('wrapped_object', wrapped_object)

    def __getattr__(self, attr):
        return getattr(self.wrapped_object, attr)

    def __setattr__(self, attr, value):
        self.monkeypatch.setattr(self.wrapped_object, attr, value,
                                 raising=False)

    def __delattr__(self, attr):
        self.monkeypatch.delattr(self.wrapped_object, attr)


@pytest.fixture()
def config(request, monkeypatch):
    from ban.core import config as ban_config
    # Make sure config cache is empty.
    ban_config.cache.clear()
    return MonkeyPatchWrapper(monkeypatch, ban_config)
