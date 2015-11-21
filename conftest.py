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
