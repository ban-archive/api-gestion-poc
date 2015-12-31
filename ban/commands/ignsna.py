import os
from peewee import IntegrityError

from ban.commands import command, report
from ban.core.models import (Municipality, PostCode)
from .helpers import session, batch, nodiff, count

__namespace__ = 'import'


@command
@nodiff
def ignsna(path, **kwargs):
    """Import from IGN/Laposte BDUNI

    :param path directory location of "hexa" files (hsp7aaaa.ai, hsv7aaaa.ai and hsw4aaaa.ai)"""

    zipcode_file = os.path.join(path, 'hsp7aaaa.ai')
    with open(zipcode_file) as f:
        m_dir = count(f)
        f.seek(0)
        batch(process_postcode_file, f, max_value=m_dir)


@session
def process_postcode_file(line):
    if line[50] != 'M':
        return report('Cedex postcode', line, report.WARNING)
    insee = line[6:11]
    post_code = line[89:94]
    version = 1
    try:
        municipality = Municipality.get(Municipality.insee == insee)
    except Municipality.DoesNotExist:
        return report('Municipality Not Existing', insee, report.WARNING)
    try:
        postcode = PostCode.get(PostCode.code == post_code)
    except PostCode.DoesNotExist:
        validator = PostCode.validator(code=post_code, version=version)
        if validator.errors:
            return report('Error on PostCode Added', validator.errors, report.ERROR)
        try:
            postcode = validator.save()
        except IntegrityError:
            return report('Error on PostCode Added', validator.errors, report.ERROR)
        report('PostCode Added', postcode, report.NOTICE)
    if postcode:
        if municipality not in postcode.municipalities:
            try:
                postcode.municipalities.add(municipality)
            except IntegrityError:
                return report('Association Already Exist', postcode, report.WARNING)
            return report('Association Done', postcode, report.NOTICE)
        return report('Association Already Exist', postcode, report.WARNING)
