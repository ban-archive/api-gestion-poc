import falcon
from ban.core import models

from ..factories import PostCodeFactory
from .utils import authorize


def test_get_postcode(get, url):
    postcode = PostCodeFactory(code="09350")
    resp = get(url('postcode-resource', identifier=postcode.id))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['code'] == '09350'


def test_get_postcode_with_code(get, url):
    PostCodeFactory(code="09350")
    resp = get(url('postcode-resource', identifier='code:09350'))
    assert resp.status == falcon.HTTP_200
    assert resp.json['id']
    assert resp.json['code'] == '09350'


@authorize
def test_create_postcode(client, url):
    assert not models.PostCode.select().count()
    data = {
        "code": "09350"
    }
    resp = client.post(url('postcode'), data)
    assert resp.status == falcon.HTTP_201
    assert resp.json['id']
    assert resp.json['code'] == '09350'
    assert models.PostCode.select().count() == 1
    uri = "https://falconframework.org{}".format(url('postcode-resource',
                                                 identifier=resp.json['id']))
    assert resp.headers['Location'] == uri
