from ban.commands import command
from ban.core import models as cmodels
from ban.core.versioning import Version

models = [Version, cmodels.Contact, cmodels.Municipality,
          cmodels.Street, cmodels.Locality, cmodels.HouseNumber,
          cmodels.Position]


@command
def syncdb(fail_silently=False):
    """Create database tables.

    fail_silently   Do not raise error if table already exists.
    """
    for model in models:
        model.create_table(fail_silently=fail_silently)
