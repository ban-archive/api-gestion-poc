import json

import peewee

from ban.commands import command, reporter
from ban.core.models import (Group, HouseNumber, Municipality, Position,
                             PostCode)
from ban.db import database
from ban.utils import compute_cia

from . import helpers

__namespace__ = 'import'


@command
@helpers.nodiff
def init(*paths, limit=0, **kwargs):
    """Initial import for real™.

    paths   Paths to json files."""
    for path in paths:
        print('Processing', path)
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
        # Use `all` to force generator evaluation.
        all(helpers.batch(process_rows, rows, chunksize=100, total=total))


@helpers.session
def process_rows(*rows):
    with database.atomic():
        for row in rows:
            process_row(row)
    return rows


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
    source = row.get('source')
    if source:
        row['attributes'] = {'source': row.pop('source')}
    validator = Municipality.validator(**row)
    if validator.errors:
        return reporter.error('Municipality errors', validator.errors)
    validator.save()
    reporter.notice('Imported Municipality', row['insee'])


def populate(keys, source, dest):
    for key in keys:
        if isinstance(key, (list, tuple)):
            dest_key = key[1]
            key = key[0]
        else:
            dest_key = key
        if key in source:
            dest[dest_key] = source[key]


def process_group(row):
    data = dict(version=1)
    keys = ['name', ('group', 'kind'), 'laposte', 'ign', 'fantoir']
    populate(keys, row, data)
    insee = row.get('municipality:insee')
    if insee:
        data['municipality'] = 'insee:{}'.format(insee)
    source = row.get('source')
    attributes = row.get('attributes', {})
    if source:
        attributes['source'] = source
    data['attributes'] = attributes
    if 'addressing' in row:
        if hasattr(Group, row['addressing'].upper()):
            data['addressing'] = row['addressing']
    update = False
    ign = data.get('ign')
    fantoir = data.get('fantoir')
    laposte = data.get('laposte')
    if fantoir:
        instance = Group.first(Group.fantoir == fantoir)
    elif ign:
        instance = Group.first(Group.ign == ign)
    elif laposte:
        instance = Group.first(Group.laposte == laposte)
    else:
        reporter.error('Missing group unique id', row)
        return
    if instance:
        attributes = getattr(instance, 'attributes') or {}
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
        reporter.error('Invalid group data', (validator.errors, row))
    else:
        try:
            validator.save()
        except peewee.IntegrityError:
            reporter.error('Integrity Error', fantoir)
        else:
            msg = 'Group updated' if instance else 'Group created'
            reporter.notice(msg, fantoir)


def process_postcode(row):
    insee = row['municipality:insee']
    municipality = 'insee:{}'.format(insee)
    source = row.get('source')
    attributes = {}
    if source:
        attributes = {'source': row.pop('source')}
    name = row.get('name')
    code = row.get('postcode')
    complement = row.get('complement')
    data = dict(name=name, code=code, municipality=municipality,
                version=1, attributes=attributes, complement=complement)
    instance = PostCode.select().join(Municipality).where(
        PostCode.complement == complement,
        PostCode.code == code,
        Municipality.insee == insee).first()
    if instance:
        return reporter.notice('PostCode already exists', code)
    validator = PostCode.validator(**data)
    if validator.errors:
        return reporter.error('PostCode errors', (validator.errors,
                                                  code, insee))
    validator.save()
    reporter.notice('Imported PostCode', code)


def process_housenumber(row):
    data = dict(version=1)
    keys = [('numero', 'number'), 'ordinal', 'ign', 'laposte', 'cia']
    populate(keys, row, data)
    fantoir = row.get('group:fantoir')
    cia = row.get('cia')
    insee = row.get('municipality:insee')
    computed_cia = None
    number = row.get('number')
    ordinal = row.get('ordinal')
    source = row.get('source')
    if source:
        data['attributes'] = {'source': source}
    # Only override if key is present (even if value is null).
    if 'postcode:code' in row:
        code = row.get('postcode:code')
        complement = row.get('postcode:complement')
        postcode = PostCode.select().join(Municipality).where(
            PostCode.code == code,
            Municipality.insee == insee,
            PostCode.complement == complement).first()
        if not postcode:
            reporter.error('HouseNumber postcode not found', (cia, code))
        else:
            data['postcode'] = postcode

    group_ign = row.get('group:ign')
    group_laposte = row.get('group:laposte')
    parent = None
    if fantoir:
        parent = 'fantoir:{}'.format(fantoir)
    elif group_ign:
        parent = 'ign:{}'.format(group_ign)
    elif group_laposte:
        parent = 'laposte:{}'.format(group_laposte)
    if parent:
        try:
            parent = Group.coerce(parent)
        except Group.DoesNotExist:
            reporter.error('Parent given but not found', parent)
            parent = None
        else:
            data['parent'] = parent

    update = False
    instance = None
    ign = row.get('ign')
    laposte = row.get('laposte')
    if cia:
        instance = HouseNumber.first(HouseNumber.cia == cia)
    elif ign:
        instance = HouseNumber.first(HouseNumber.ign == ign)
    elif laposte:
        instance = HouseNumber.first(HouseNumber.laposte == laposte)
    if parent and not instance:
        # Data is not coerced yet, we want None for empty strings.
        ordinal = row.get('ordinal') or None
        instance = HouseNumber.first(HouseNumber.parent == parent,
                                     HouseNumber.number == data['number'],
                                     HouseNumber.ordinal == ordinal)
    if instance:
        attributes = getattr(instance, 'attributes') or {}
        if attributes.get('source') == source:
            # Reimporting same data?
            reporter.warning('HouseNumber already exists', (instance.cia, instance.ign, instance.laposte))
            return
        data['version'] = instance.version + 1
        update = True

    if not instance and not parent:
        reporter.error('No matching instance and missing parent reference',
                       row)
        return

    validator = HouseNumber.validator(instance=instance, update=update, **data)
    if validator.errors:
        reporter.error('HouseNumber errors', (validator.errors, data))
        return
    with HouseNumber._meta.database.atomic():
        try:
            validator.save()
        except peewee.IntegrityError as e:
            reporter.warning('HouseNumber DB error', (data, str(e)))
        else:
            msg = 'HouseNumber Updated' if instance else 'HouseNumber created'
            reporter.notice(msg, data)


def process_position(row):
    positioning = row.get('positionning')  # two "n" in the data.
    if not positioning or not hasattr(Position, positioning.upper()):
        positioning = Position.OTHER
    source = row.get('source')
    cia = row.get('housenumber:cia')
    housenumber_ign = row.get('housenumber:ign')
    housenumber = None
    if cia:
        cia = cia.upper()
        housenumber = HouseNumber.first(HouseNumber.cia == cia)
    elif housenumber_ign:
        housenumber = HouseNumber.first(HouseNumber.ign == housenumber_ign)
    if not housenumber:
        reporter.error('Unable to find parent housenumber', row)
        return
    instance = None
    if 'ign' in row:
        # The only situation where we want to avoid creating new position is
        # when we have the ign identifier.
        instance = Position.first(Position.ign == row['ign'])
    version = instance.version + 1 if instance else 1
    data = dict(source=source, housenumber=housenumber,
                positioning=positioning, version=version)
    kind = row.get('kind', '')
    if hasattr(Position, kind.upper()):
        data['kind'] = kind
    elif not instance:
        # We are creating a new position (not updating), kind is mandatory.
        kind = Position.UNKNOWN
    if kind:
        data['kind'] = kind
    populate(['ign', 'name', ('geometry', 'center')], row, data)
    validator = Position.validator(instance=instance, update=bool(instance),
                                   **data)
    if validator.errors:
        reporter.error('Position error', validator.errors)
    else:
        try:
            position = validator.save()
        except peewee.IntegrityError as e:
            reporter.error('Integrity error', (str(e), data))
        else:
            msg = 'Position updated' if instance else 'Position created'
            reporter.notice(msg, position.id)
