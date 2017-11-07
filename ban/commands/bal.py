import peewee

from ban.commands import command, reporter
from ban.core.models import HouseNumber, Group, Position
from ban.db import database

from . import helpers

__namespace__ = 'import'


@command
@helpers.nodiff
def bal(path, limit=0, **kwargs):
    """Import from BAL files (AITF 1.1 format)
    cf https://github.com/etalab/ban/issues/75
    """
    # We need to support BOM.
    rows = list(helpers.load_csv(path, encoding='utf-8-sig'))
    if limit:
        rows = rows[:limit]
    # Use `all` to force generator evaluation.
    all(helpers.batch(process_rows, rows, total=len(rows)))


@helpers.session
def process_rows(*rows):
    with database.atomic():
        for row in rows:
            process_row(row)
    return rows


def process_row(row):
    id = row.get('uid_adresse', '').strip()
    name = row.get('voie_nom')
    insee, group_id, *_ = row.get('cle_interop').split('_')
    if len(group_id) == 4:  # This is a FANTOIR code.
        fantoir = insee + group_id
        group_id = None
    else:
        fantoir = None
    if row.get('numero') == '99999':
        process_group(row, id, name, insee, group_id, fantoir)
    else:
        process_housenumber(row, id, name, insee, group_id, fantoir)


def process_group(row, id, name, insee, group_id, fantoir):
    municipality = 'insee:{}'.format(insee)
    data = dict(name=name, fantoir=fantoir, municipality=municipality)
    instance = None  # Means creation.
    if id:
        try:
            instance = Group.get(Group.id == id)
        except Group.DoesNotExist:
            return reporter.error('Group id not found', id)
    elif data['fantoir']:
        try:
            instance = Group.get(Group.fantoir == data['fantoir'])
        except Group.DoesNotExist:
            pass  # Let's create it.
    if instance:
        data['kind'] = instance.kind
        # Well… the BAL can't give us a BAN reference version, be kind for now.
        # See https://github.com/etalab/ban/issues/91#issuecomment-198432574
        # and https://github.com/etalab/ban/issues/94
        data['version'] = instance.version + 1
    else:
        data['kind'] = Group.WAY
    validator = Group.validator(instance=instance, **data)
    if validator.errors:
        reporter.error('Invalid data', validator.errors)
    else:
        street = validator.save()
        msg = 'Created group' if not instance else 'Updated group'
        reporter.notice(msg, street.id)
        if row.get('lat') and row.get('long'):
            process_housenumber(row, id, name, insee, group_id, fantoir)


def process_housenumber(row, id, name, insee, group_id, fantoir):
    number = row.get('numero')
    if number == '99999':
        # Means it's a group address point, according to AITF weird specs.
        number = None
    ordinal = row.get('suffixe') or None
    lat = row.get('lat')
    lon = row.get('long')
    kind = row.get('position')
    cia = None
    instance = None
    data = dict(number=number, ordinal=ordinal)
    if id:
        instance = HouseNumber.where(HouseNumber.id == id).first()
        if not instance:
            return reporter.error('HouseNumber id not found', id)
        parent = instance.parent
    elif fantoir:
        parent = 'fantoir:{}'.format(fantoir)
        cia = instance.cia
    elif group_id:
        parent = Group.where(Group.id == group_id).first()
        if not parent:
            return reporter.error('Group id not found', group_id)
        if parent.fantoir:
            cia = instance.cia
    else:
        return reporter.error('Missing group id and fantoir', id)
    if cia:
        instance = HouseNumber.where(HouseNumber.cia == cia).first()
    if instance:
        # Well… the BAL can't give us a BAN reference version, be kind for now.
        # See https://github.com/etalab/ban/issues/91#issuecomment-198432574
        # and https://github.com/etalab/ban/issues/94
        data['version'] = instance.version + 1
        data['instance'] = instance
    data['parent'] = parent

    validator = HouseNumber.validator(**data)
    if validator.errors:
        reporter.error('HouseNumber errors', (validator.errors, parent))
    else:
        try:
            housenumber = validator.save()
        except peewee.IntegrityError:
            return reporter.error('Duplicate housenumber',
                                  (number, ordinal, parent))
        if lon and lat:
            process_position(housenumber, (lon, lat), kind)
        msg = 'HouseNumber Updated' if instance else 'HouseNumber created'
        reporter.notice(msg, (number, ordinal, parent))


KIND_MAPPING = {
    'bâtiment': Position.BUILDING,
    'délivrance postale': Position.POSTAL,
    'entrée': Position.ENTRANCE,
    'cage d’escalier': Position.STAIRCASE,
    'logement': Position.UNIT,
    'parcelle': Position.PARCEL,
    'segment': Position.SEGMENT,
    'service technique': Position.UTILITY,
}


def process_position(housenumber, center, kind):
    kind = KIND_MAPPING.get(kind, kind)
    instance = Position.where(Position.housenumber == housenumber,
                              Position.kind == kind).first()
    version = instance.version + 1 if instance else 1
    validator = Position.validator(housenumber=housenumber, center=center,
                                   source='BAL',  # Use siren from filename?
                                   positioning=Position.IMAGERY,
                                   kind=kind, instance=instance,
                                   version=version)
    if validator.errors:
        reporter.error('Position error', validator.errors)
    else:
        position = validator.save()
        msg = 'Position updated' if instance else 'Position created'
        reporter.notice(msg, position.id)
