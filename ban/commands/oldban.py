import json

from ban.commands import command, report
from ban.core.models import (HouseNumber, Locality, Municipality, Position,
                             Street, PostCode)

from .helpers import batch, iter_file, nodiff, session, load_csv

__namespace__ = 'import'


@command
@nodiff
def oldban(path, **kwargs):
    """Import from BAN json stream files from
    http://bano.openstreetmap.fr/BAN_odbl/"""
    total = sum(1 for line in iter_file(path))
    print('Done computing file size')
    rows = iter_file(path, formatter=json.loads)
    batch(process_row, rows, chunksize=100, total=total)


@session
def process_row(metadata):
    name = metadata.get('name')
    id = metadata.get('id')
    insee = metadata.get('citycode')
    postcode = metadata.get('postcode')
    fantoir = ''.join(id.split('_')[:2])[:9]

    kind = metadata['type']
    klass = Street if kind == 'street' else Locality
    instance = klass.select().where(klass.fantoir == fantoir).first()
    if instance:
        return report('Existing {}'.format(klass.__name__),
                      {name: name, fantoir: fantoir},
                      report.WARNING)

    try:
        municipality = Municipality.get(Municipality.insee == insee)
    except Municipality.DoesNotExist:
        return report('Municipality does not exist', insee, report.ERROR)

    with PostCode._meta.database.atomic():
        postcode, created = PostCode.get_or_create(
            code=postcode,
            municipality=municipality,
            defaults={'version': 1, 'name': municipality.name})

    data = dict(
        name=name,
        fantoir=fantoir,
        municipality=municipality.id,
        version=1,
    )
    validator = klass.validator(**data)

    if not validator.errors:
        item = validator.save()
        report(kind, item, report.NOTICE)
        housenumbers = metadata.get('housenumbers')
        if housenumbers:
            for id, metadata in housenumbers.items():
                add_housenumber(item, id, metadata, postcode)
    else:
        report('Street error', validator.errors, report.ERROR)


def add_housenumber(parent, id, metadata, postcode):
    number, *ordinal = id.split(' ')
    ordinal = ordinal[0] if ordinal else ''
    center = [metadata['lon'], metadata['lat']]
    ign = metadata.get('id')

    validator = HouseNumber.validator(number=number, ordinal=ordinal,
                                      version=1, parent=parent.id, ign=ign,
                                      ancestors=[postcode])

    if not validator.errors:
        housenumber = validator.save()
        validator = Position.validator(center=center, version=1,
                                       kind=Position.ENTRANCE,
                                       housenumber=housenumber.id)
        if not validator.errors:
            validator.save()
            report('Position', validator.instance, report.NOTICE)
        else:
            report('Position error', validator.errors, report.ERROR)
        report('Housenumber', housenumber, report.NOTICE)
    else:
        report('Housenumber error', validator.errors, report.ERROR)


@command
@nodiff
def cea(path, **kwargs):
    """Import CEA from IGN Adresse Premium
    File: Lien_Adresse-Hexa_D0{xx}-ED141.csv."""
    rows = list(load_csv(path))
    batch(add_cea, rows, total=len(rows))


def add_cea(row):
    ign = row.get('ID_ADR')
    laposte = row.get('HEXACLE_1')
    if laposte == 'NR':
        return report('Missing CEA', ign, report.ERROR)
    query = HouseNumber.update(laposte=laposte).where(HouseNumber.ign == ign)
    done = query.execute()
    if not done:
        return report('IGN id not found', ign, report.ERROR)
    report('Done', ign, report.NOTICE)
