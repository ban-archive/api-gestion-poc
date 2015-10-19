import pytest

from ban.core import context
from ban.core.tests.factories import UserFactory


@pytest.fixture()
def user():
    return UserFactory()


@pytest.fixture()
def staffuser():
    return UserFactory(is_staff=True)


@pytest.fixture()
def loggedclient(client, user):
    context.set_user(user)
    client.login(username=user.username, password='password')
    return client


# @pytest.fixture()
# def loggedapp(app, user):
#     """Return an app with an already logged in user."""
#     form = app.get(reverse('login')).forms['login']
#     form['username'] = user.serial
#     form['password'] = 'password'
#     form.submit().follow()
#     setattr(app, 'user', user)  # for later use, if needed
#     return app


# @pytest.fixture()
# def staffapp(app, staffuser):
#     """Return an app with an already logged in staff user."""
#     form = app.get(reverse('login')).forms['login']
#     form['username'] = staffuser.serial
#     form['password'] = 'password'
#     form.submit().follow()
#     setattr(app, 'user', staffuser)  # for later use, if needed
#     return app
