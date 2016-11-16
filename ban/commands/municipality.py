from ban.commands import command, reporter
from ban.core import models
from ban.core import versioning
from . import helpers


@command
@helpers.session
def merge(destination, sources=[], name='', label='', **kwargs):
    if destination in sources:
        helpers.abort('Destination in sources')
    if name == '':
        helpers.abort('Name should not be empty')
    if label == '':
        helpers.abort('Label should not be empty')
    try:
        destination = models.Municipality.get(
            models.Municipality.insee == destination)
    except models.Municipality.DoesNotExist:
        helpers.abort('Destination does not exist')
    if not sources:
        helpers.abort('No sources')
    sources_inst = []
    # Make sure all sources exist before processing any of them.
    for source in sources:
        try:
            source = models.Municipality.get(
                models.Municipality.insee == source)
        except models.Municipality.DoesNotExist:
            helpers.abort('Source {} does not exist'.format(source))
        else:
            sources_inst.append(source)
    process_destination(destination, name)
    source_done = []
    for source in sources_inst:
        if source.insee not in source_done:
            source_done.append(source.insee)
            process_source(destination, source)


def process_source(destination, source):
    versioning.Redirect.add(destination, 'insee', source.insee)
    process_redirect(destination, source)
    source.delete_instance()


def process_destination(destination, name):
    process_redirect(destination, destination)
    destination.name = name
    destination.increment_version()
    destination.save()


def process_redirect(destination, source):
    group_area = models.Group.validator(
        name=source.name,
        municipality=destination,
        version=1, kind='area', attributes={'insee': source.insee})
    group_area.save()
    gr_area = models.Group.select().where(
        models.Group.name == source.name).first()
    postcodes = models.PostCode.select().where(
        models.PostCode.municipality == source)
    for postcode in postcodes:
        postcode.municipality = destination
        postcode.increment_version()
        postcode.save()
    groups = models.Group.select().where(models.Group.municipality == source)
    for group in groups:
        if group != gr_area:
            group.municipality = destination
            group.increment_version()
            group.save()
            housenumbers = models.HouseNumber.select().where(
                models.HouseNumber.parent == group)
            for housenumber in housenumbers:
                housenumber.ancestors = gr_area
                housenumber.increment_version()
                housenumber.save()
