from ..factories import GroupFactory


def test_cors(get):
    street = GroupFactory(name="Rue des Boulets")
    resp = get('/group/id:' + str(street.id))
    assert resp.headers["Access-Control-Allow-Origin"] == "*"
    assert resp.headers["Access-Control-Allow-Headers"] == "X-Requested-With"
