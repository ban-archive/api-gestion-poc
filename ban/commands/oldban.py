import json

import peewee

from ban.commands import command, report
from ban.core.models import (HouseNumber, Group, Municipality, Position,
                             PostCode)

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
    code = metadata.get('postcode')
    fantoir = ''.join(id.split('_')[:2])[:9]

    kind = 'area' if metadata['type'] == 'locality' else 'way'
    instance = Group.select().where(Group.fantoir == fantoir).first()
    if instance:
        return report('Existing {}'.format(Group.__name__),
                      {name: name, fantoir: fantoir},
                      report.WARNING)

    try:
        municipality = Municipality.get(Municipality.insee == insee)
    except Municipality.DoesNotExist:
        return report('Municipality does not exist', insee, report.ERROR)

    validator = PostCode.validator(code=code, version=1,
                                   name=municipality.name,
                                   municipality=municipality)
    if validator.errors:
        report('Invalid postcode', code, report.ERROR)
        postcode = None
    else:
        with PostCode._meta.database.atomic():
            try:
                postcode = validator.save()
            except peewee.IntegrityError:
                # Another thread created it?
                postcode = PostCode.get(PostCode.code == code)
            else:
                report('Created postcode', code, report.NOTICE)

    validator = Group.validator(name=name, fantoir=fantoir, kind=kind,
                                municipality=municipality.pk, version=1)

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
    data = dict(number=number, ordinal=ordinal, version=1, parent=parent.pk,
                ign=ign)
    if postcode:
        data['postcodes'] = [postcode]

    validator = HouseNumber.validator(**data)

    if not validator.errors:
        housenumber = validator.save()
        validator = Position.validator(center=center, version=1,
                                       kind=Position.ENTRANCE,
                                       housenumber=housenumber.pk)
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
    try:
        done = query.execute()
    except peewee.IntegrityError:
        report('Duplicate CEA', laposte, report.ERROR)
    else:
        if not done:
            return report('IGN id not found', ign, report.ERROR)
        report('Done', ign, report.NOTICE)
