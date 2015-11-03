import json

import pytest
from urllib import parse

from falcon.testing.srmock import StartResponseMock
from falcon.testing.helpers import create_environ

from ban.core import context
from ban.tests.factories import UserFactory

from ban import db
from ban.commands.db import models, syncdb
from ban.http import app


def pytest_configure(config):
    db.test.connect()
    for model in models:
        model._meta.database = db.test
    syncdb(fail_silently=True)
    verbose = config.getoption('verbose')
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


def pytest_unconfigure(config):
    db.test.drop_tables(models)
    db.test.close()


def pytest_runtest_setup(item):
    for model in models[::-1]:
        model.delete().execute()
        assert not len(model.select())


@pytest.fixture()
def user():
    return UserFactory()


@pytest.fixture()
def staffuser():
    return UserFactory(is_staff=True)


def fake_request(path, **kwargs):
    parsed = parse.urlparse(path)
    path = parsed.path
    if parsed.query:
        kwargs['query_string'] = parsed.query
    resp = StartResponseMock()
    body = app(create_environ(path, **kwargs), resp)
    resp.headers = resp.headers_dict
    resp.status = int(resp.status.split(' ')[0])
    resp.body = body[0].decode() if body else ''
    if 'application/json' in resp.headers.get('Content-Type', ''):
        resp.json = json.loads(resp.body)
    return resp
fake_request._ = 'client'


@pytest.fixture()
def get():

    def _(path, **kwargs):
        return fake_request(path, method='GET', **kwargs)

    return _


@pytest.fixture()
def post():

    def _(path, data, **kwargs):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = parse.urlencode(data)
        return fake_request(path, method='POST', body=body, headers=headers,
                            **kwargs)

    return _


@pytest.fixture()
def put():

    def _(path, **kwargs):
        return fake_request(path, method='PUT', **kwargs)

    return _


@pytest.fixture()
def loggedclient(client, user):
    context.set_user(user)
    client.login(username=user.username, password='password')
    return client


@pytest.fixture()
def url():
    def _(klass, **kwargs):
        url = None
        for route in klass.routes()[::-1]:
            try:
                url = route.format(**kwargs)
            except KeyError:
                continue
            else:
                break
        print(url)
        return url
    return _
