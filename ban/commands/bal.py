import peewee

from ban.commands import command, report
from ban.core.models import HouseNumber, Group, Position
from ban.utils import compute_cia

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
    helpers.batch(process_row, rows, total=len(rows))


@helpers.session
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
            return report('Group id not found', id, report.ERROR)
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
        report('Invalid data', validator.errors, report.ERROR)
    else:
        street = validator.save()
        msg = 'Created group' if not instance else 'Updated group'
        report(msg, street.id, report.NOTICE)
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
            return report('HouseNumber id not found', id, report.ERROR)
        parent = instance.parent
    elif fantoir:
        parent = 'fantoir:{}'.format(fantoir)
        cia = compute_cia(insee, fantoir[5:], number, ordinal)
    elif group_id:
        parent = Group.where(Group.id == group_id).first()
        if not parent:
            return report('Group id not found', group_id, report.ERROR)
        if parent.fantoir:
            cia = compute_cia(parent.fantoir[:5], parent.fantoir[5:], number,
                              ordinal)
    else:
        return report('Missing group id and fantoir', id, report.ERROR)
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
        report('HouseNumber errors', (validator.errors, parent), report.ERROR)
    else:
        try:
            housenumber = validator.save()
        except peewee.IntegrityError:
            return report('Duplicate housenumber', (number, ordinal, parent),
                          report.ERROR)
        if lon and lat:
            process_position(housenumber, (lon, lat), kind)
        msg = 'HouseNumber Updated' if instance else 'HouseNumber created'
        report(msg, (number, ordinal, parent), report.NOTICE)


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
        report('Position error', validator.errors, report.ERROR)
    else:
        validator.save()
        msg = 'Position updated' if instance else 'Position created'
        report(msg, center, report.NOTICE)
