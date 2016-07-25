from ban.auth import models
from ban.tests.factories import UserFactory


def test_user_password_is_hashed():
    password = '!22@%lkjsdfé&'
    user = UserFactory()
    user.set_password(password)
    # Reload from db.
    user = models.User.get(models.User.id == user.id)
    assert user.password != password
    assert user.check_password(password)
