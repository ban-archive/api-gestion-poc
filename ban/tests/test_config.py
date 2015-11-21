import os

import pytest


def test_config_should_use_defaults(config):
    assert config.DB_NAME == 'ban'


def test_config_should_use_environ(config):
    os.environ['FOOBAR'] = 'barfoo'
    assert config.FOOBAR == 'barfoo'
    os.environ.pop('FOOBAR')


def test_config_should_give_environ_priority_over_defaults(config):
    os.environ['DB_NAME'] = 'barfoo'
    assert config.DB_NAME == 'barfoo'


def test_config_should_give_cache_priority_over_environ(config):
    os.environ['DB_NAME'] = 'barfoo'
    config.DB_NAME = 'newvalue'
    assert config.DB_NAME == 'newvalue'


def test_config_should_raise_for_unkown_attr(config):
    with pytest.raises(AttributeError):
        config.FOOBAR


def test_config_get_should_accept_default(config):
    assert config.get('FOOBAR', 'defaultvalue') == 'defaultvalue'


def test_config_get_should_return_none_if_missing_and_no_default(config):
    assert config.get('FOOBAR') == None


def test_config_set_should_normalize_key(config):
    config.set('db-password', 'password')
    assert config.DB_PASSWORD == 'password'
