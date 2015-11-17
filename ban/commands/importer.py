from ban.commands import command, report
from ban.core import models
from ban.core.versioning import Diff

from .helpers import batch, load_csv, session

__namespace__ = 'import'


@command
def municipalities(path, update=False, departement=None):
    """Import municipalities from
    http://www.collectivites-locales.gouv.fr/files/files/epcicom2015.csv.

    update          allow to override already existing Municipality
    departement     only import departement (insee id: 01, 31, 2A…)
    """
    rows = load_csv(path, encoding='latin1')
    Diff.ACTIVE = False  # No diff for initial imports.
    if departement:
        rows = [r for r in rows if r['dep_epci'] == str(departement)]
    batch(add_municipality, rows, max_value=len(list(rows)))


@session
def add_municipality(data, update=False):
    insee = data.get('insee')
    name = data.get('nom_com')
    siren = data.get('siren_com')
    version = 1
    try:
        instance = models.Municipality.get(models.Municipality.insee == insee)
    except models.Municipality.DoesNotExist:
        instance = None
    if instance and not update:
        return report('Existing', name)

    data = dict(insee=insee, name=name, siren=siren, version=version)
    validator = models.Municipality.validator(**data)
    if not validator.errors:
        validator.save(instance=instance)
    else:
        return report('Error', validator.errors)
