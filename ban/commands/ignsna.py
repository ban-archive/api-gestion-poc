import glob
import os
from ban.commands import command, report
from ban.core.models import (HouseNumber, Locality, Municipality, Position,
                             Street, ZipCode)
from .helpers import iter_file, session, batch

__namespace__ = 'import'


@command
def ignsna(path, **kwargs):
    """Import from IGN/Laposte BDUNI
    :param path: directory location of the files hsp7xxxx.ai, hsv7xxxx.ai and hsw4xxxx.ai"""

    municipality_zipcode_file = glob.glob(os.path.join(path, 'hsp7*.ai'))
    # street_file = glob.glob(os.path.join(path, 'hsv7*.ai'))
    # number_file = glob.glob(os.path.join(path, 'hsw4*.ai'))

    if municipality_zipcode_file is not None:
        max_value = get_max_line(municipality_zipcode_file[0])
        lines = list(get_lines(municipality_zipcode_file[0]))
        # ToDo: test the performance of single threaded and multi-threaded processes
        batch(process_municipality_file, lines, max_value=max_value)

        # ToDo: uncomment and complete when process needed
        # if street_file is not None:
        #     process_streetFile(street_file[0])
        #
        # if number_file is not None:
        #     process_numberFile(number_file[0])


@session
def process_municipality_file(line):
    # line = lines[x]
    if line[50] == 'M':
        insee = line[6:11]
        # name = line[11:49]
        # name = name.strip()
        zip_code = line[89:94]
        # old_insee = line[126:131]
        # old_insee = old_insee.strip()

        zip_code_bean = ZipCode.create_or_get(code=zip_code, version='1')
        try:
            municipality = Municipality.get(Municipality.insee == insee)
            code = municipality.zipcodes
            if not (zip_code_bean[0]) in code:
                if zip_code_bean[0]:
                    try:
                        municipality.zipcodes.add(zip_code_bean[0])
                    except municipality.IntegrityError:
                        pass
        except Municipality.DoesNotExist:
            pass


# ToDo: uncomment and complete when process needed
# @session
# def process_streetFile(street_file):
#     max_value = get_max_line(street_file)
#     lines = get_lines(street_file)
#     pbar = ProgressBar()
#     for x in pbar(range(0, max_value)):
#         line = lines[x]
#         if line[0] == 'V':
#             insee = line[7:12]
#             name = line[60:92]
#             name = name.strip()
#             zip_code = line[109:114]
#             try:
#                 municipality = Municipality.get(Municipality.insee == insee)
#
#             except Municipality.DoesNotExist:
#                 return report('Error', 'Municipality does not exist: {}'.format(insee))
#
#             try:
#                 street = Street.get(Street.name == name and Street.municipality == municipality.id)
#             except Street.DoesNotExist:
#                 data = dict(
#                     name=name,
#                     municipality=municipality.id,
#                     version=1,
#                     # tempory fantoir
#                     fantoir='999999',
#                     zipcode=zip_code,
#                 )
#                 validator = Street.validator(**data)
#                 if not validator.errors:
#                     item = validator.save()
#                 else:
#                     report('Error', validator.errors)


def get_lines(file):
    f = open(file)
    lines = f.readlines()
    return lines


def get_max_line(file):
    max_value = sum(1 for line in iter_file(file))
    return max_value

# ToDo: uncomment and complete when process needed
# def process_numberFile(numberfile):
#     pass
