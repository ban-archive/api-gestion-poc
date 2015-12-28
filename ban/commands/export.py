from pathlib import Path

from ban.commands import command, report

from ban.core import models
from ban.core.encoder import dumps


@command
def resources(path, **kwargs):
    """Export database as resources in json stream format.

    path    path of file where to write resources
    """
    resources = [models.PostCode, models.Municipality, models.Locality,
                 models.Street, models.HouseNumber]
    with Path(path).open(mode='w', encoding='utf-8') as f:
        for resource in resources:
            for data in resource.select().as_resource_list():
                f.write(dumps(data) + '\n')
                # Memory consumption when exporting all France housenumbers?
                report(resource.__name__, data, report.NOTICE)
