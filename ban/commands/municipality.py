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
        print(source)
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
    with db.atomic():
        process_postcode(destination, destination, label)
        group_to_municipality(destination, destination, areas, label)
        for source in sources_inst:
            if source.insee not in source_done:
                source_done.append(source.insee)
                process_source(destination, source, areas, label)
        validator = models.Municipality.validator(
            instance=destination,
            name=name,
            version=destination.version+1,
            update=True)
        if validator.errors:
            reporter.error('Errors', validator)
        else:
            validator.save()
            reporter.notice('name modified', destination)
        print(reporter)
        if helpers.confirm('Are you confident with those changes ?') is False:
            db.rollback()
            reporter.clear('Action cancelled')


def process_source(destination, source, areas, label):
    versioning.Redirect.add(destination, 'insee', source.insee)
    versioning.Redirect.add(destination, 'id', source.id)
    reporter.notice('redirected to destination', source)
    process_postcode(destination, source, label)
    group_to_municipality(destination, source, areas, label)
    source.delete_instance()


def group_to_municipality(destination, source, areas, label):
    validator = models.Group.validator(
        name=source.name,
        municipality=destination,
        version=1,
        kind=models.Group.AREA,
        attributes={'insee': source.insee})
    if validator.errors:
        reporter.error('Errors', validator)
    else:
        reporter.notice('Created', validator)
        gr_area = validator.save()
        areas.append(gr_area)
        for group in source.groups:
            if group not in areas:
                move_group(destination, group)
                for housenumber in group.housenumber_set:
                    validator = models.HouseNumber.validator(
                        instance=housenumber,
                        ancestors=[gr_area],
                        update=True,
                        version=housenumber.version+1)
                    if validator.errors:
                        reporter.error('Errors', housenumber)
                    else:
                        validator.save()
                        reporter.notice('Ancestor redirected', housenumber)


def process_postcode(destination, source, label):
    for postcode in source.postcodes:
        if postcode.complement is None:
            validator = models.PostCode.validator(
                instance=postcode,
                municipality=destination,
                update=True,
                complement=postcode.name,
                name=label,
                version=postcode.version+1)
        else:
            validator = models.PostCode.validator(
                instance=postcode,
                municipality=destination,
                update=True,
                name=label,
                version=postcode.version+1
                )
        if validator.errors:
            reporter.error('Errors', validator)
        else:
            validator.save()
            reporter.notice('label and municipality modified', postcode)


def move_group(destination, group):
    validator = models.Group.validator(
        instance=group,
        municipality=destination,
        update=True,
        version=group.version+1)
    if validator.errors:
        reporter.error('Errors', validator)
    else:
        validator.save()
        reporter.notice('municipality modified', group)
