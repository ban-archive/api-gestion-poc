from ban.auth import models as amodels
from ban.commands import command
from ban.core import models as cmodels
from ban.core.versioning import Diff, Version

from .helpers import abort, confirm

models = [Version, Diff, amodels.User, amodels.Client, amodels.Grant,
          amodels.Session, amodels.Token, cmodels.Municipality,
          cmodels.Street, cmodels.Locality, cmodels.HouseNumber,
          cmodels.Position]


@command
def create(fail_silently=False, **kwargs):
    """Create database tables.

    fail_silently   Do not raise error if table already exists.
    """
    for model in models:
        model.create_table(fail_silently=fail_silently)


@command
def truncate(force=False, **kwargs):
    """Truncate database tables.

    force   Do not ask for confirm.
    """
    if not force and not confirm('Are you sure?', default=False):
        abort('Aborted.')
    # Delete in reverse way not to break FK constraints.
    for model in models[::-1]:
        model.delete().execute()
