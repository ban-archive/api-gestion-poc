import string

from ban.auth.utils import generate_secret


def test_generate_secret():
    assert len(generate_secret(10)) == 10


def test_generate_secret_honour_given_chars():
    assert generate_secret(chars=string.digits).isdigit()
