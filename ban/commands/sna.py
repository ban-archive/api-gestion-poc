from pathlib import Path

import peewee

from ban.commands import command, report
from ban.core.models import PostCode, Group, HouseNumber
from .helpers import session, batch, nodiff, file_len, Bar

__namespace__ = 'import'


MATRICULE_TO_CEA = {}


@command
@nodiff
def sna(path, group=False, postcode=False, housenumber=False, **kwargs):
    """Import postcodes from IGN/Laposte BDUNI

    path        directory location of "hexa" files (hsp7aaaa.ai, hsv7aaaa.ai
                and hsw4aaaa.ai)
    group       Whether to run group import or not.
    postcode    Whether to run postcode import or not.
    group       Whether to run postcode import or not.
    """
    # p7 => code postaux
    # v7 => voies
    # w4 => cea des voies et des numéros, et les numéros
    load_cea(path)
    if group:
        with Path(path, 'hsv7aaaa.ai').open(encoding='latin1') as f:
            batch(process_group, f, total=file_len(f))
    if postcode:
        with Path(path).joinpath('hsp7aaaa.ai').open(encoding='latin1') as f:
            batch(process_postcode, f, total=file_len(f))
    if housenumber:
        with Path(path).joinpath('hsw4aaaa.ai').open(encoding='latin1') as f:
            batch(process_housenumber, f, total=file_len(f))


def load_cea(path):
    with Path(path, 'hsw4aaaa.ai').open(encoding='latin1') as f:
        for line in f:
            matricule = line[:8]
            numero = line[8:12].strip()
            cea = line[23:33]
            if not numero:
                MATRICULE_TO_CEA[matricule] = cea


AREA_VALUES = ['LD', 'LOT', 'RES', 'ZA']


def guess_kind(name, group_kind):
    if group_kind in AREA_VALUES:
        return Group.AREA
    elif (not group_kind and not name.startswith('CHEMIN')
          and not name.startswith('RUE')):
        return Group.AREA
    else:
        return Group.WAY


@session
def process_group(line):
    if not line[0] == 'V':
        return report('Not a street', line, report.NOTICE)
    name = line[60:92]
    matricule = line[12:20]
    laposte = MATRICULE_TO_CEA.get(matricule)
    if not laposte:
        return report('Missing CEA', matricule, report.ERROR)
    municipality = 'insee:{}'.format(line[7:12])
    kind = guess_kind(name, line[92:96].strip())

    validator = Group.validator(name=name, laposte=laposte,
                                municipality=municipality, kind=kind)
    if validator.errors:
        report('Error', validator.errors, report.ERROR)
    else:
        validator.save()
        report('Success', name, report.NOTICE)


@session
def process_postcode(line):
    if line[50] != 'M':
        return report('Cedex postcode', line, report.WARNING)
    municipality = 'insee:{}'.format(line[6:11])
    code = line[89:94]
    name = line[90:]
    validator = PostCode.validator(code=code, name=name,
                                   municipality=municipality)
    if validator.errors:
        return report('PostCode Error', validator.errors, report.ERROR)
    else:
        with PostCode._meta.database.atomic():
            try:
                validator.save()
            except peewee.IntegrityError:
                report('Already created', (code, municipality), report.WARNING)
            else:
                report('PostCode created', code, report.NOTICE)


@session
def process_housenumber(line):
    matricule = line[:8]
    number = line[8:12].strip()
    ordinal = line[13:23].strip()
    laposte = line[23:33]
    group_laposte = MATRICULE_TO_CEA.get(matricule)
    group = 'laposte:{}'.format(group_laposte)
    if not group_laposte:
        return report('Missing group CEA', matricule, report.ERROR)
    if not number:
        return report('Not a housenumber', laposte, report.NOTICE)
    validator = HouseNumber.validator(number=number, ordinal=ordinal,
                                      laposte=laposte, parent=group)
    if validator.errors:
        report('Housenumber error', validator.errors, report.ERROR)
    else:
        validator.save()
        report('Housenumber created', laposte, report.NOTICE)


@command
def filter_hsw4(hsv7, hsw4, output, **kwargs):
    """Filter hswa according to a hsv7 one. For dev only."""
    wanted = []
    with Path(hsv7).open(encoding='latin1') as f:
        for line in f:
            wanted.append(line[12:20])
    with Path(output).open('w', encoding='latin1') as f1:
        with Path(hsw4).open(encoding='latin1') as f2:
            total = file_len(f2)
            bar = Bar(total=total, throttle=1000)
            for line in f2:
                if line[:8] in wanted:
                    f1.write(line)
                bar.update()
