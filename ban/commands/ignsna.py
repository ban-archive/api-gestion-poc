import os
from ban.commands import command, report
from ban.core.models import (Municipality, PostCode)
from .helpers import session, batch

__namespace__ = 'import'


@command
def ignsna(path, **kwargs):
    """Import from IGN/Laposte BDUNI
    :param path: directory location of the files hsp7aaaa.ai, hsv7aaaa.ai and hsw4aaaa.ai"""

    municipality_zipcode_file = os.path.join(path, 'hsp7aaaa.ai')
    if municipality_zipcode_file is not None:
        lines = open(municipality_zipcode_file).readlines()
        batch(process_municipality_file, lines, max_value=len(lines))


@session
def process_municipality_file(line):
    if line[50] == 'M':
        insee = line[6:11]
        post_code = line[89:94]
        version = 1
        try:
            municipality = Municipality.get(Municipality.insee == insee)
        except Municipality.DoesNotExist:
            return report('Municipality Not Existing', insee, report.WARNING)
        if municipality:
            try:
                postcode = PostCode.get(PostCode.code == post_code)
            except PostCode.DoesNotExist:
                postcode = None
                data = dict(code=post_code, version=version)
                validator = PostCode.validator(instance=postcode, **data)
                if not validator.errors:
                    postcode = validator.save()
                    report('PostCode Added', postcode, report.NOTICE)
                else:
                    report('Error on PostCode Added', validator.errors, report.ERROR)
            if postcode:
                if municipality in postcode.municipalities:
                    report('Association Already Exist', postcode, report.WARNING)
                else:
                    postcode.municipalities.add(municipality)
                    report('Association Done', postcode, report.NOTICE)
