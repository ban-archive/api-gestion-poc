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
        # default is only called for unknown types, calling super would raise
        # TypeError, which we don't want.
        return str(o)


def dumps(data):
    return json.dumps(data, cls=ResourceEncoder)
