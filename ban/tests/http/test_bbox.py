from ban.core import models

from ..factories import (HouseNumberFactory, PositionFactory)
from .utils import authorize


@authorize
def test_bbox(get):
    position = PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    resp = get('/bbox?north=2&south=0&west=0&east=2')
    assert len(resp.json['collection']) == 1


@authorize
def test_bbox_allows_floats(get):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    resp = get('/bbox?north=2.23&south=0.12&west=0.56&east=2.34')
    assert len(resp.json['collection']) == 1


@authorize
def test_missing_bbox_param_returns_bad_request(get):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    resp = get('/bbox?north=1&south=0&west=0')
    assert resp.status_code == 400


@authorize
def test_invalid_bbox_param_returns_bad_request(get):
    PositionFactory(center=(1, 1))
    PositionFactory(center=(-1, -1))
    resp = get('/bbox?north=2&south=0&west=0&east=invalid')
    assert resp.status_code == 400


@authorize
def test_hn_is_not_duplicated_with_unique_in_bbox(get):
    position = PositionFactory(center=(1, 1))
    PositionFactory(center=(1.1, 1.1), housenumber=position.housenumber)
    resp = get('/bbox?north=2&south=0&west=0&east=2&unique=true')
    assert len(resp.json['collection']) == 1