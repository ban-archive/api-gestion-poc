from ban.http.utils import link
from ..factories import MunicipalityFactory


def test_cors_headers(get):
    municipality = MunicipalityFactory()
    resp = get('/municipality/{}'.format(municipality.id))
    assert resp.headers['Access-Control-Allow-Origin'] == '*'


def test_invalid_route(get):
    municipality = MunicipalityFactory()
    resp = get('/municipalities/{}'.format(municipality.id))
    assert resp.status_code == 404
    assert resp.json['error'] == 'Path not found'


def test_method_not_allowed(client):
    resp = client.patch('/municipality/')
    assert resp.status_code == 405
    assert resp.json['error'] == 'Method not allowed'


def test_link_headers():
    headers = {}
    link(headers, 'http://ban.fr', 'alternate')
    assert headers == {'Link': '<http://ban.fr>; rel=alternate'}
    link(headers, 'http://another.fr', 'alternate')
    assert headers == {
        'Link': '<http://ban.fr>; rel=alternate, <http://another.fr>; rel=alternate'  # noqa
    }
