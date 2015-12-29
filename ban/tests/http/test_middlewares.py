from ..factories import StreetFactory


def test_cors(get):
    street = StreetFactory(name="Rue des Boulets")
    resp = get('/street/id:' + str(street.id))
    assert resp.headers["Access-Control-Allow-Origin"] == "*"
    assert resp.headers["Access-Control-Allow-Headers"] == "X-Requested-With"
