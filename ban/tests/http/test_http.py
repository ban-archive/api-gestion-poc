from ..factories import MunicipalityFactory


def test_cors_headers(get):
    municipality = MunicipalityFactory()
    resp = get('/municipality/{}'.format(municipality.id))
    assert resp.headers['Access-Control-Allow-Origin'] == '*'
