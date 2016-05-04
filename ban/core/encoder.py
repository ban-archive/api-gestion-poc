import json
from datetime import datetime
from postgis import Geometry
from ban.commands.reporter import Reporter


class ResourceEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, Geometry):
            return o.geojson
        elif isinstance(o, Reporter):
            return o.__json__()
        try:
            return super().default(o)
        except TypeError:
            return str(o)


def dumps(data):
    return json.dumps(data, cls=ResourceEncoder)
