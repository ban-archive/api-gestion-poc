from pathlib import Path

import peewee

from ban.commands import command, report
from ban.core.models import Municipality, PostCode
from .helpers import session, batch, nodiff, file_len

__namespace__ = 'import'


@command
@nodiff
def ignsna(path, **kwargs):
    """Import postcodes from IGN/Laposte BDUNI

    path    directory location of "hexa" files (hsp7aaaa.ai, hsv7aaaa.ai and
            hsw4aaaa.ai)"""

    with Path(path).joinpath('hsp7aaaa.ai').open() as f:
        batch(process_postcode, f, max_value=file_len(f))


@session
def process_postcode(line):
    if line[50] != 'M':
        return report('Cedex postcode', line, report.WARNING)
    insee = line[6:11]
    code = line[89:94]
    try:
        municipality = Municipality.get(Municipality.insee == insee)
    except Municipality.DoesNotExist:
        return report('Municipality Not Existing', insee, report.WARNING)
    postcode, created = PostCode.get_or_create(code=code, version=1)
    if created:
        report('PostCode Added', postcode, report.NOTICE)
    try:
        postcode.municipalities.add(municipality)
    except peewee.IntegrityError:
        report('Association Already Exists', postcode, report.WARNING)
    else:
        report('Association Added', postcode, report.NOTICE)
