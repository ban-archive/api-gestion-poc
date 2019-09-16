from urllib.parse import quote

from werkzeug.exceptions import HTTPException
from flask import Response

from ban.core.encoder import dumps


def abort(code, headers=None, **kwargs):
    description = dumps(kwargs)
    response = Response(status=code, mimetype='application/json',
                        response=description, headers=headers)
    raise HTTPException(description=description, response=response)


def get_bbox(args):
    bbox = {}
    params = ['north', 'south', 'east', 'west']
    for param in params:
        try:
            bbox[param] = float(args.get(param))
        except ValueError:
            abort(400, error='Invalid value for {}: {}'.format(
                param, args.get(param)))
        except TypeError:
            # None (param not set).
            continue
    if not len(bbox) == 4:
        return None
    return bbox


def check_merge_params(args):
    compulsory_params = ["erased_group_id", "master_group_version", "prior_position"]
    errors = {}
    for param in compulsory_params:
        if param not in args:
            errors[param] = "Value should not be null"

    prior_position_choices = ["erased", "master"]
    if "prior_position" in args.keys() and args["prior_position"] not in prior_position_choices:
        errors["prior_position"] = "'{}' should be one of the following choices: {}".format(
            args["prior_position"], ", ".join(prior_position_choices))
    if len(errors):
        abort(422, error="Invalid data", errors=errors)


def get_search_params(args):
    enum_types = ['strict', 'case', 'abbrev', 'libelle', 'ponctuation', 'direct', 'approx']
    type = args.get('searchType') if args.get('searchType') is not None else 'strict'
    search = args.get('searchName')
    if type not in enum_types and search is not None:
        abort(400, error='Invalid value for searchType: {}. Value must be {}'.format(type, str(enum_types)))
    return {'type': type, 'search': search}


# Do not encode them, as per RFC 3986
RESERVED = ":/?#[]@!$&'()*+,;="


def link(headers, target, rel):
    headers.setdefault('Link', '')
    link = '<' + quote(target, safe=RESERVED) + '>; rel=' + rel
    if headers['Link']:
        link = ', ' + link
    headers['Link'] += link
