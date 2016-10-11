from pathlib import Path

from ban.commands import command, reporter

from ban.core import models
from ban.core.encoder import dumps


@command
def resources(path, **kwargs):
    """Export database as resources in json stream format.

    path    path of file where to write resources
    """
    resources = [models.PostCode, models.Municipality, models.Group,
                 models.HouseNumber]
    with Path(path).open(mode='w', encoding='utf-8') as f:
        for resource in resources:
            for data in resource.select().serialize({'*': {}}):
                f.write(dumps(data) + '\n')
                reporter.notice(resource.__name__, data)
