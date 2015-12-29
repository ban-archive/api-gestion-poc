import falcon
from ban.auth import models

from .utils import authorize


@authorize
def test_create_user(client, url):
    # Client user + session user == 2
    assert models.User.select().count() == 2
    resp = client.post('/user', {
        'username': 'newuser',
        'email': 'test@test.com',
    })
    assert resp.status == falcon.HTTP_201
    assert models.User.select().count() == 3
    uri = "https://falconframework.org{}".format(url('user-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri


@authorize
def test_cannot_create_user_without_username(client):
    assert models.User.select().count() == 2
    resp = client.post('/user', {
        'username': '',
        'email': 'test@test.com',
    })
    assert resp.status == falcon.HTTP_422
    assert models.User.select().count() == 2


@authorize
def test_cannot_create_user_without_email(client):
    assert models.User.select().count() == 2
    resp = client.post('/user', {
        'username': 'newuser',
        'email': '',
    })
    assert resp.status == falcon.HTTP_422
    assert models.User.select().count() == 2


def test_cannot_create_user_if_not_authenticated(client):
    assert not models.User.select().count()
    resp = client.post('/user', {
        'username': 'newuser',
        'email': 'test@test.com',
    })
    assert resp.status == falcon.HTTP_401
    assert not models.User.select().count()
