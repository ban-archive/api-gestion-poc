import json

import peewee

from ban.commands import command, reporter
from ban.core.models import (Group, HouseNumber, Municipality, Position,
                             PostCode)
from ban.utils import compute_cia

from . import helpers

__namespace__ = 'import'


@command
@helpers.nodiff
def init(*paths, limit=0, **kwargs):
    """Initial import for real™.

    paths   Paths to json files."""
    for path in paths:
        rows = helpers.iter_file(path, formatter=json.loads)
        if limit:
            print('Running with limit', limit)
            extract = []
            for i, row in enumerate(rows):
                if i >= limit:
                    break
                extract.append(row)
            rows = extract
            total = limit
        else:
            print('Computing file size')
            total = sum(1 for line in helpers.iter_file(path))
            print('Done computing file size')
        helpers.batch(process_row, rows, chunksize=100, total=total)


@helpers.session
def process_row(row):
    kind = row.pop('type')
    if kind == "municipality":
        return process_municipality(row)
    elif kind == "group":
        return process_group(row)
    elif kind == "postcode":
        return process_postcode(row)
    elif kind == "housenumber":
        return process_housenumber(row)
    elif kind == "position":
        return process_position(row)
    else:
        return reporter.error('Missing "type" key', row)


def process_municipality(row):
    row['attributes'] = {'source': row.pop('source')}
    validator = Municipality.validator(**row)
    if validator.errors:
        return reporter.error('Municipality errors', validator.errors)
    validator.save()
    reporter.notice('Imported Municipality', row['insee'])


def process_group(row):
    municipality = 'insee:{}'.format(row.get('municipality:insee'))
    fantoir = row.get('group:fantoir')
    name = row.get('name')
    kind = row.get('group')
    source = row.get('source')
    attributes = row.get('attributes', {})
    attributes['source'] = source
    data = dict(name=name, fantoir=fantoir, municipality=municipality,
                kind=kind, version=1, attributes=attributes)
    update = False
    instance = Group.first(Group.fantoir == fantoir)
    if instance:
        attributes = getattr(instance, 'attributes', {})
        if attributes.get('source') == source:
            # Reimporting same data?
            reporter.warning('Group already exist', fantoir)
            return
        data['version'] = instance.version + 1
        if attributes:
            attributes.update(data['attributes'])
            data['attributes'] = attributes
        update = True
    validator = Group.validator(instance=instance, update=update, **data)
    if validator.errors:
        reporter.error('Invalid group data', validator.errors)
    else:
        group = validator.save()
        reporter.notice('Created group', group.id)


def process_postcode(row):
    insee = row['municipality:insee']
    municipality = 'insee:{}'.format(insee)
    attributes = {'source': row.pop('source')}
    name = row.get('name')
    code = row.get('postcode')
    data = dict(name=name, code=code, municipality=municipality,
                version=1, attributes=attributes)
    instance = PostCode.select().join(Municipality).where(
        PostCode.code == code, Municipality.insee == insee).first()
    if instance:
        return reporter.notice('PostCode already exists', code)
    validator = PostCode.validator(**data)
    if validator.errors:
        return reporter.error('PostCode errors', (validator.errors,
                                                  code, insee))
    validator.save()
    reporter.notice('Imported PostCode', code)


def process_housenumber(row):
    number = row.get('numero')
    ordinal = row.get('ordinal') or None
    fantoir = row.get('group:fantoir')
    insee = fantoir[:5]
    cia = row.get('cia')
    computed_cia = compute_cia(insee, fantoir[5:], number, ordinal)
    if not cia:
        cia = computed_cia
    parent = 'fantoir:{}'.format(fantoir)
    source = row.get('source')
    attributes = {'source': source}
    data = dict(number=number, ordinal=ordinal, version=1, parent=parent,
                attributes=attributes)
    if 'ref:ign' in row:
        data['ign'] = row.get('ref:ign')
    if 'postcode' in row:
        code = row.get('postcode')
        postcode = PostCode.select().join(Municipality).where(
            PostCode.code == code,
            Municipality.insee == insee).first()
        if not postcode:
            reporter.error('HouseNumber postcode not found', (cia, code))
        else:
            data['postcode'] = postcode
    instance = HouseNumber.first(HouseNumber.cia == cia)
    update = False
    if instance:
        if cia != computed_cia:
            # Means new values are changing one of the four values of the cia
            # (insee, fantoir, number, ordinal). Make sure we are not creating
            # a duplicate.
            duplicate = HouseNumber.first(HouseNumber.cia == computed_cia)
            if duplicate:
                msg = 'Duplicate CIA'
                reporter.error(msg, (cia, computed_cia))
                return
        attributes = getattr(instance, 'attributes') or {}
        if attributes.get('source') == source:
            # Reimporting same data?
            reporter.warning('HouseNumber already exists', instance.cia)
            return
        data['version'] = instance.version + 1
        update = True

    validator = HouseNumber.validator(instance=instance, update=update, **data)
    if validator.errors:
        reporter.error('HouseNumber errors', (validator.errors, parent))
        return
    with HouseNumber._meta.database.atomic():
        try:
            validator.save()
        except peewee.IntegrityError:
            reporter.warning('HouseNumber DB error', cia)
        else:
            msg = 'HouseNumber Updated' if instance else 'HouseNumber created'
            reporter.notice(msg, (number, ordinal, parent))


def process_position(row):
    kind = row.get("kind")
    source = row.get("source")
    cia = row.get('housenumber:cia').upper()
    center = row.get('geometry')
    housenumber = HouseNumber.first(HouseNumber.cia == cia)
    if not housenumber:
        reporter.error('Position housenumber does not exist', cia)
        return
    instance = Position.first(Position.housenumber == housenumber,
                              Position.kind == kind, Position.source == source)
    version = instance.version + 1 if instance else 1
    data = dict(kind=kind, source=source, housenumber=housenumber,
                center=center, positioning=Position.OTHER, version=version)
    validator = Position.validator(instance=instance, **data)
    if validator.errors:
        reporter.error('Position error', validator.errors)
    else:
        position = validator.save()
        msg = 'Position updated' if instance else 'Position created'
        reporter.notice(msg, position.id)
