import json

import peewee

from ban.commands import command, reporter
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
        return reporter.warning('Existing group', {name: name,
                                                   fantoir: fantoir})

    try:
        municipality = Municipality.get(Municipality.insee == insee)
    except Municipality.DoesNotExist:
        return reporter.error('Municipality does not exist', insee)

    validator = PostCode.validator(code=code, version=1,
                                   name=municipality.name,
                                   municipality=municipality)
    if validator.errors:
        reporter.error('Invalid postcode', code)
        postcode = None
    else:
        with PostCode._meta.database.atomic():
            try:
                postcode = validator.save()
            except peewee.IntegrityError:
                # Another thread created it?
                postcode = PostCode.get(PostCode.code == code)
            else:
                reporter.notice('Created postcode', code)

    validator = Group.validator(name=name, fantoir=fantoir, kind=kind,
                                municipality=municipality.pk, version=1)

    if not validator.errors:
        try:
            item = validator.save()
        except peewee.IntegrityError:
            return reporter.error('Duplicate group', fantoir)
        reporter.notice(kind, item)
        housenumbers = metadata.get('housenumbers')
        if housenumbers:
            for id, metadata in housenumbers.items():
                add_housenumber(item, id, metadata, postcode)
    else:
        reporter.error('Street error', validator.errors)


def add_housenumber(parent, id, metadata, postcode):
    number, *ordinal = id.split(' ')
    ordinal = ordinal[0] if ordinal else ''
    center = [metadata['lon'], metadata['lat']]
    ign = metadata.get('id')
    data = dict(number=number, ordinal=ordinal, version=1, parent=parent.pk,
                ign=ign)
    if postcode:
        data['postcode'] = postcode

    validator = HouseNumber.validator(**data)

    if not validator.errors:
        housenumber = validator.save()
        validator = Position.validator(center=center, version=1,
                                       kind=Position.ENTRANCE,
                                       positioning=Position.OTHER,
                                       housenumber=housenumber.pk)
        if not validator.errors:
            validator.save()
            reporter.notice('Position', validator.instance)
        else:
            reporter.error('Position error', validator.errors)
        reporter.notice('Housenumber created', housenumber)
    else:
        reporter.error('Housenumber error', validator.errors)


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
        return reporter.error('Missing CEA', ign)
    query = HouseNumber.update(laposte=laposte).where(HouseNumber.ign == ign)
    try:
        done = query.execute()
    except peewee.IntegrityError:
        reporter.error('Duplicate CEA', laposte)
    else:
        if not done:
            return reporter.error('IGN id not found', ign)
        reporter.notice('Done', ign)
