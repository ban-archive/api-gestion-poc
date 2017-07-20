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
    'PostCode': PostCode.select(),
    'Municipality': Municipality.select(),
    'Group': Group.select(),
    'HouseNumber': HouseNumber.select(),
    'Position': Position.select()
}


@command
def resources(resource, path, **kwargs):
    """Export database as resources in json stream format.

    path    path of file where to write resources
    resource Municipality, PostCode, Group, HouseNumber or Position
    """
    resources = ['Municipality', 'PostCode', 'Group', 'HouseNumber', 'Position']
    if resource not in resources:
        helpers.abort('Resource {} does not exists'.format(resource))
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
