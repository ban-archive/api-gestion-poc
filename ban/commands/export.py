from pathlib import Path
import os

import peewee

from ban.commands import command
from ban.core.encoder import dumps
from ban.core.models import (Group, HouseNumber, Municipality, Position,
                             PostCode)
from ban.db import database

from . import helpers

QUERIES = {
    PostCode: PostCode.select().join(Municipality),
    Municipality: Municipality.select(),
    Group: Group.select().join(Municipality),
    HouseNumber: (HouseNumber.select().join(Group, on=HouseNumber.parent == Group.pk)  # noqa
                                      .join(Position, peewee.JOIN_LEFT_OUTER, on=Position.housenumber == HouseNumber.pk)  # noqa
                                      .group_by(HouseNumber.pk)),
}


@command
def resources(path, **kwargs):
    """Export database as resources in json stream format.

    path    path of file where to write resources
    """
    resources = [Municipality, PostCode, Group, HouseNumber]
    for resource in resources:
        query = QUERIES.get(resource)
        filename = '{}.ndjson'.format(resource.__name__.lower())
        with Path(path).joinpath(filename).open(mode='w') as f:
            print('Exporting to', f.name)
            query = query.order_by(resource.pk)
            results = []
            for result in helpers.batch(process_resource, query,
                                        chunksize=1000, total=query.count()):
                results.append(result)
                if len(results) == 10000:
                    f.write('\n'.join(results) + '\n')
                    f.flush()
                    results = []
            if results:
                f.write('\n'.join(results) + '\n')


def process_resource(*rows):
    with database.execution_context():  # Reset connection in current process.
        results = []
        for row in rows:
            results.append(dumps(row.as_export))
        return results
