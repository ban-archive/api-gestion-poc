from ban.commands import command, report
from ban.core import models

from . import helpers

__namespace__ = 'import'


@command
@helpers.nodiff
def municipalities(path, update=False, departement=None, **kwargs):
    """Import municipalities from
    http://www.collectivites-locales.gouv.fr/files/files/epcicom2015.csv.

    update          allow to override already existing Municipality
    departement     only import this departement id
    """
    rows = helpers.load_csv(path, encoding='latin1')
    if departement:
        rows = [r for r in rows if r['dep_epci'] == str(departement)]
    else:
        # We can't read it twice (for counting the len), let's load it for now.
        rows = list(rows)
    helpers.batch(add_municipality, rows, max_value=len(rows))


@helpers.session
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
        return report('Existing', name, report.WARNING)

    data = dict(insee=insee, name=name, siren=siren, version=version)
    validator = models.Municipality.validator(instance=instance, **data)
    if not validator.errors:
        instance = validator.save()
        report('Processed', instance, report.NOTICE)
    else:
        report('Error', validator.errors, report.ERROR)
