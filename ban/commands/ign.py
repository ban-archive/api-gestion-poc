import peewee

from . import command, helpers, report

from ban.core.models import Group, PostCode, HouseNumber, Position

__namespace__ = "import"


@command
@helpers.nodiff
def ign_group(paths=[], **kwargs):
    """Import IGN street and locality CSV exports.

    paths   Paths to street and locality CSV files."""
    for path in paths:
        rows = helpers.load_csv(path)
        rows = list(rows)
        helpers.batch(process_group, rows, total=len(rows))


@helpers.session
def process_group(row):
    name = row.get('nom')
    fantoir = row.get('id_fantoir')
    municipality = 'insee:{}'.format(row.get('code_insee'))
    ign = row.get('identifiant_fpb')
    data = dict(name=name, fantoir=fantoir, municipality=municipality, ign=ign,
                kind=Group.WAY)
    laposte = row.get('id_poste') or None
    if laposte:
        data['laposte'] = laposte
    validator = Group.validator(**data)
    if validator.errors:
        report('Je suis pas content', validator.errors, report.ERROR)
    else:
        validator.save()
        report('Je suis content', name, report.NOTICE)


@command
@helpers.nodiff
def ign_postcode(path, **kwargs):
    """Import from IGN postcode CSV exports.

    path   Path to postcode CSV files."""
    rows = helpers.load_csv(path)
    rows = list(rows)
    helpers.batch(process_postcode, rows, total=len(rows))


@helpers.session
def process_postcode(row):
    name = row.get('libelle')
    municipality = 'insee:{}'.format(row.get('code_insee'))
    code = row.get('code_post')
    validator = PostCode.validator(name=name, municipality=municipality,
                                   code=code)
    if validator.errors:
        report('Postcode error', validator.errors, report.ERROR)
    else:
        validator.save()
        report('Postcode saved', code, report.NOTICE)


@command
@helpers.nodiff
def ign_housenumber(path, **kwargs):
    """Import from IGN housenumbers CSV exports.

    path   Path to housenumbers CSV files."""
    rows = helpers.load_csv(path)
    rows = list(rows)
    helpers.batch(process_housenumber, rows, total=len(rows))


@helpers.session
def process_housenumber(row):
    number = row.get('numero')
    ordinal = row.get('rep')
    parent = 'ign:{}'.format(row.get('identifiant_fpb'))
    postcode = 'code:{}'.format(row.get('code_post'))
    complement = row.get('designation_de_l_entree')
    ign = row.get('id')
    lat = row.get('lat')
    lon = row.get('lon')
    localisation_type = row.get('type_de_localisation')
    data = dict(number=number, ordinal=ordinal, ign=ign, parent=parent,
                postcodes=postcode)
    laposte = row.get('cea')
    if laposte:
        data['laposte'] = laposte
    validator = HouseNumber.validator(**data)
    if validator.errors:
        report('HouseNumber error', validator.errors, report.ERROR)
    else:
        try:
            housenumber = validator.save()
        except peewee.IntegrityError as e:
            report('SQL Error ', str(e), report.ERROR)
        else:
            report('HouseNumber created', (number, ordinal), report.NOTICE)
            if localisation_type != 'Au centre commune':
                process_position(housenumber, (lon, lat), localisation_type,
                                 {'complement': complement})
            else:
                report('Skipped centre commune', str(housenumber),
                       report.NOTICE)


def process_position(housenumber, center, localisation_type, attributes):
    if localisation_type == 'Interpolée':
        positioning = Position.INTERPOLATION
    elif localisation_type == 'Projetée du centre parcelle':
        positioning = Position.PROJECTION
    else:
        positioning = Position.OTHER
    validator = Position.validator(housenumber=housenumber, center=center,
                                   attributes=attributes, source='IGN',
                                   positioning=positioning,
                                   kind=Position.ENTRANCE)
    if validator.errors:
        report('Position error', validator.errors, report.ERROR)
    else:
        validator.save()
        report('Position created', center, report.NOTICE)
