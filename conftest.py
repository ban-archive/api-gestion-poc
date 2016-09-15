import json

import pytest
from flask import url_for
from flask.testing import FlaskClient

from ban import db
from ban.commands.db import create as createdb
from ban.commands.db import truncate as truncatedb
from ban.commands.db import models
from ban.commands.reporter import Reporter
from ban.core import context
from ban.http.api import app as application
from ban.tests.factories import SessionFactory, TokenFactory, UserFactory


def pytest_configure(config):
    assert db.test.database.startswith('test_')
    for model in models:
        model._meta.database = db.test
    db.test.connect()
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


@pytest.fixture
def post(client):
    return client.post


@pytest.fixture
def patch(client):
    return client.patch


@pytest.fixture
def put(client):
    return client.put


class Client(FlaskClient):

    def open(self, *args, **kwargs):
        if len(args) == 2:
            # Be smart, allow to pass data as arg, even if EnvironBuilder want
            # it as kwarg only.
            kwargs['data'] = args[1]
            args = args[0],
        # Allow to define headers and content_type before opening the request.
        kwargs.setdefault('headers', {})
        kwargs['headers'].update(getattr(self, 'extra_headers', {}))
        if hasattr(self, 'content_type') and not kwargs.get('content_type'):
            kwargs['content_type'] = self.content_type
        if kwargs.get('content_type') == 'application/json':
            if 'data' in kwargs:
                kwargs['data'] = json.dumps(kwargs['data'])
        return super().open(*args, **kwargs)

application.test_client_class = Client


@pytest.fixture()
def url():
    def _(endpoint, **kwargs):
        if 'id' in kwargs:
            # Allow to create "id:value" identifiers from kwargs.
            kwargs['identifier'] = '{identifier}:{id}'.format(**kwargs)
            del kwargs['id']
        if not isinstance(endpoint, str):  # Passing the resource.
            endpoint = endpoint.endpoint
        uri = url_for(endpoint, **kwargs)
        uri = 'http://localhost{}'.format(uri)
        return uri
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


@pytest.fixture
def reporter():
    reporter_ = Reporter(2)
    context.set('reporter', reporter_)
    return reporter_
