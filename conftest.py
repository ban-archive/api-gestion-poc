import json
from urllib.parse import urlencode

import pytest
from flask import url_for

from ban import db
from ban.commands.db import create as createdb
from ban.commands.db import truncate as truncatedb
from ban.commands.db import models
from ban.commands.reporter import Reporter
from ban.core import context
from ban.http.api import api, app as application
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


class Client:
    def __init__(self, client):
        self.client = client
        self.headers = {}

    def call(self, verb, uri, data=None):
        method = getattr(self.client, verb)
        return method(uri, data=json.dumps(data),
                      content_type='application/json',
                      headers=self.headers)

    def get(self, url, data):
        return self.call('get', url, data)

    def patch(self, url, data):
        return self.call('patch', url, data)

    def put(self, url, data):
        return self.call('put', url, data)

    def post(self, url, data):
        return self.call('post', url, data)

    def delete(self, url):
        return self.call('delete', url)


@pytest.fixture
def test_client(client):
    return Client(client)


@pytest.fixture()
def url():
    def _(endpoint, **kwargs):
        if not isinstance(endpoint, str):
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
