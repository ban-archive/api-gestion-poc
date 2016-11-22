from ban.commands import command, reporter
from ban.core import models
from ban.core import versioning
from . import helpers


@command
@helpers.session
def merge(destination, sources=[], name='', label='', **kwargs):
    """
    Municipality merge command.
    Steps:
    - for each Municipality to be removed:
    - create a new Group with its name
    - attach all HouseNumbers of this Municipality to this new Group
    - attach sources Groups and sources PostCodes to destination
    - Remove the Municipality
    """
    if destination in sources:
        helpers.abort('Destination in sources')
    if not name or not name.split():
        helpers.abort('Name should not be empty')
    if not label or not label.split():
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
    source_done = []
    areas = []
    db = models.Municipality._meta.database
    db.begin()
    for source in sources_inst:
        if source.insee not in source_done:
            source_done.append(source.insee)
            process_source(destination, source, areas, label)
    process_destination(destination, areas, name, label)
    print(reporter)
    if helpers.confirm('Do you feel confident with those changes ?'):
        db.commit()
    else:
        db.rollback()


def process_source(destination, source, areas, label):
    versioning.Redirect.add(destination, 'insee', source.insee)
    versioning.Redirect.add(destination, 'id', source.id)
    reporter.notice('redirected to destination', source)
    process_postcode(destination, source, label)
    process_source_to_group(destination, source, areas, label)
    source.delete_instance()


def process_destination(destination, areas, name, label):
    process_postcode(destination, destination, label)
    process_source_to_group(destination, destination, areas, label)
    destination.name = name
    destination.increment_version()
    destination.save()
    reporter.notice('name modified', destination)


def process_source_to_group(destination, source, areas, label):
    validator = models.Group.validator(
        name=source.name,
        municipality=destination,
        version=1, kind=models.Group.AREA, attributes={'insee': source.insee})
    if validator.errors:
        reporter.error('Errors', validator)
    else:
        reporter.notice('Created', validator)
    gr_area = validator.save()
    areas.append(gr_area)
    for group in source.groups:
        move_group(destination, group, areas)
        for housenumber in group.housenumber_set:
            housenumber.ancestors.add(gr_area)
            housenumber.increment_version()
            housenumber.save()
            reporter.notice('Ancestor redirected', housenumber)


def process_postcode(destination, source, label):
    for postcode in source.postcodes:
        postcode.municipality = destination
        postcode.attributes = {'ligne6': label}
        postcode.increment_version()
        postcode.save()
        reporter.notice('label and municipality modified', postcode)


def move_group(destination, group, areas):
    if group not in areas:
        group.municipality = destination
        group.increment_version()
        group.save()
        reporter.notice('municipality modified', group)
