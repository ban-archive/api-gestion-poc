from werkzeug.exceptions import HTTPException
from flask import Response

from ban.core.encoder import dumps


def abort(code, **kwargs):
    description = dumps(kwargs)
    response = Response(status=code, mimetype='application/json',
                        response=description)
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
