from ban.http.utils import link
from ..factories import MunicipalityFactory


def test_cors_headers(get):
    municipality = MunicipalityFactory()
    resp = get('/municipality/{}'.format(municipality.id))
    assert resp.headers['Access-Control-Allow-Origin'] == '*'


def test_link_headers():
    headers = {}
    link(headers, 'http://ban.fr', 'alternate')
    assert headers == {'Link': '<http://ban.fr>; rel=alternate'}
    link(headers, 'http://another.fr', 'alternate')
    assert headers == {
        'Link': '<http://ban.fr>; rel=alternate, <http://another.fr>; rel=alternate'  # noqa
    }
