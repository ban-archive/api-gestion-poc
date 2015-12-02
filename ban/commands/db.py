from ban.auth import models as amodels
from ban.commands import command, report
from ban.core import models as cmodels
from ban.core.versioning import Diff, Version, IdentifierRedirect

from . import helpers

models = [Version, Diff, IdentifierRedirect, amodels.User, amodels.Client,
          amodels.Grant, amodels.Session, amodels.Token, cmodels.ZipCode,
          cmodels.Municipality,
          cmodels.Municipality.zipcodes.get_through_model(),
          cmodels.Street, cmodels.Locality, cmodels.HouseNumber,
          cmodels.Position]


@command
def create(fail_silently=False, **kwargs):
    """Create database tables.

    fail_silently   Do not raise error if table already exists.
    """
    for model in models:
        model.create_table(fail_silently=fail_silently)
        report('Created', model.__name__)


@command
def truncate(force=False, names=[], **kwargs):
    """Truncate database tables.

    force   Do not ask for confirm.
    names   List of model names to truncate (in the given order).
    """
    if not names:
        # We expect names, not classes.
        names = [m.__name__.lower() for m in models]
        msg = 'Truncate all tables?'
    else:
        msg = 'Truncate tables: {}'.format(', '.join(names))
    if not force and not helpers.confirm(msg, default=False):
        helpers.abort('Aborted.')
    # Delete in reverse way not to break FK constraints.
    for model in models[::-1]:
        name = model.__name__.lower()
        if name not in names:
            continue
        model.delete().execute()
        report('Truncated', name)
