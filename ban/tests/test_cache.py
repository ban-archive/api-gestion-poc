from ban.db import cache
from ban.core import models

from . import factories


def test_set_should_add_in_the_cache():
    cache.set(['1', '2'], 'value')
    assert cache.STORE['1|2'] == 'value'


def test_get_should_retrieve_from_the_cache():
    cache.set(['1', '2'], 'value')
    assert cache.get(['1', '2']) == 'value'


def test_cache_should_add_to_the_cache_only_if_not_yet_set():
    cache.cache('key', lambda *args, **kwargs: 'value')
    assert cache.STORE['key'] == 'value'
    cache.cache('key', lambda *args, **kwargs: 'othervalue')
    assert cache.STORE['key'] == 'value'


def test_clear_should_clear_the_cache():
    cache.set('key', 'value')
    assert cache.STORE
    cache.clear()
    assert not cache.STORE


def test_group_municipality_should_be_cached(sql_spy):
    mun = factories.MunicipalityFactory()
    group1 = factories.GroupFactory(municipality=mun)
    group2 = factories.GroupFactory(municipality=mun)
    # Load the models from scratch, otherwise Diff creation has already
    # populated the "municipality" property
    group1 = models.Group.first(models.Group.pk == group1.pk)
    group2 = models.Group.first(models.Group.pk == group1.pk)
    sql_spy.reset_mock()
    assert sql_spy.call_count == 0
    assert group1.municipality == mun
    assert sql_spy.call_count == 1
    assert group2.municipality == mun
    assert sql_spy.call_count == 1


def test_saving_should_clear_cache(sql_spy):
    mun = factories.MunicipalityFactory()
    group1 = factories.GroupFactory(municipality=mun)
    group2 = factories.GroupFactory(municipality=mun)
    # Load the models from scratch, otherwise Diff creation has already
    # populated the "municipality" property
    group1 = models.Group.first(models.Group.pk == group1.pk)
    group2 = models.Group.first(models.Group.pk == group1.pk)
    sql_spy.reset_mock()
    assert sql_spy.call_count == 0
    assert group1.municipality == mun
    assert sql_spy.call_count == 1
    mun.version = 2
    mun.save()
    sql_spy.reset_mock()
    assert sql_spy.call_count == 0
    assert group2.municipality.version == 2
    assert sql_spy.call_count == 1
