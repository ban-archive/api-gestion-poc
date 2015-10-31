import json

import pytest
from urllib import parse

from falcon.testing.srmock import StartResponseMock
from falcon.testing.helpers import create_environ

from ban.core import context
from ban.core.tests.factories import UserFactory

from ban.core.database import test_db, db
from ban.core import models as cmodels
from ban.versioning import models as vmodels
from ban.http.views import app

models = [vmodels.Version, cmodels.Contact, cmodels.Municipality,
          cmodels.Street, cmodels.Locality, cmodels.HouseNumber,
          cmodels.Position]


def pytest_configure(config):
    test_db.connect()
    for model in models:
        model._meta.database = test_db
    for model in models:
        model.create_table(fail_silently=True)
    verbose = config.getoption('verbose')
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


def pytest_unconfigure(config):
    db.drop_tables(models)
    test_db.close()


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
