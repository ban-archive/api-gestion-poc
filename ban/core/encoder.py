import json
from datetime import datetime
from postgis import Geometry


class ResourceEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, Geometry):
            return o.geojson
        try:
            return super().default(o)
        except TypeError:
            return str(o)


def dumps(data):
    return json.dumps(data, cls=ResourceEncoder)
