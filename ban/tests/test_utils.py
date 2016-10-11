from ban.utils import parse_mask


def test_parse_mask():
    source = 'field,field2,relation.field,relation.field2,relation.relation2.field,relation.relation2.relation3.field,field3'  # noqa
    assert parse_mask(source) == {
        'field': {},
        'field2': {},
        'field3': {},
        'relation': {
            'field': {},
            'field2': {},
            'relation2': {
                'field': {},
                'relation3': {
                    'field': {}
                }
            }
        }
    }
