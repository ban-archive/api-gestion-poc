import falcon

from ..factories import PositionFactory
from .utils import authorize


@authorize
def test_diff_endpoint(client):
    position = PositionFactory()
    position.center = (10, 20)
    position.increment_version()
    position.save()
    housenumber = position.housenumber
    housenumber.ordinal = "ter"
    housenumber.increment_version()
    housenumber.save()
    street = housenumber.street
    old_street_name = street.name
    street.name = "Rue des Musiciens"
    street.increment_version()
    street.save()
    resp = client.get('/diff')
    assert resp.status == falcon.HTTP_200
    assert 'collection' in resp.json
    # Created: Municipality, Street, HouseNumber, Position
    # Modified: Street, HouseNumber, Position
    diffs = resp.json['collection']
    assert len(diffs) == 7
    street_create_diff = diffs[1]
    assert street_create_diff['increment'] == diffs[0]['increment'] + 1
    assert street_create_diff['old'] == None
    assert street_create_diff['new']['id'] == street.id
    assert street_create_diff['resource_id'] == street.id
    street_update_diff = diffs[-1]
    assert street_update_diff['old']['id'] == street.id
    assert street_update_diff['new']['id'] == street.id
    assert street_update_diff['diff']['name'] == {
        "old": old_street_name,
        "new": "Rue des Musiciens"
    }


@authorize
def test_diff_endpoint_accept_increment_parameter(client):
    position = PositionFactory()
    resp = client.get('/diff')
    assert len(resp.json['collection']) == 4
    increment = resp.json['collection'][-1]['increment']
    position.center = (3, 4)
    position.increment_version()
    position.save()
    resp = client.get('/diff')
    assert len(resp.json['collection']) == 5
    resp = client.get('/diff?increment={}'.format(increment))
    assert len(resp.json['collection']) == 1
    assert resp.json['collection'][0]['increment'] == increment + 1


def test_diff_endpoint_is_protected(client):
    resp = client.get('/diff')
    assert resp.status == falcon.HTTP_401
