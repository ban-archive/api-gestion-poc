from ban.commands import command, reporter
from ban.core import models
from . import helpers


@command
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
    for source in sources_inst:
        process_source(destination, source)


def process_source(destination, source):
    # Redirection (si on recherche 01002, on recoit 01001).
    # Creation group_area.
    # HouseNumber
    # Delete source
    pass

# @command
# def oldmerge(insee_maitresse, insee_secondaire, name_nouvelle_commune,libelle_nouvelle_commune, **kwargs):
#     insee_secondaire = insee_secondaire.split(',')
#
#     name_area_maitresse = mun_maitresse.name
#     mun_maitresse.name = name_nouvelle_commune
#     mun_maitresse.version += 1
#     mun_maitresse.save()
#     group_area_maitresse = Group()
#     group_area_maitresse.kind = 'area'
#     group_area_maitresse.name = name_area_maitresse
#     group_area_maitresse.created_by_id = 1
#     group_area_maitresse.modified_by_id = 1
#     group_area_maitresse.municipality = mun_maitresse
#     group_area_maitresse.save()
#     pc_maitresse = PostCode.get(PostCode.municipality == mun_maitresse)
#     if pc_maitresse.name is None:
#         pc_maitresse.name = libelle_nouvelle_commune
#     group_rue_maitresse = Group.select().where(Group.municipality == mun_maitresse)
#     for gr_rue_maitresse in group_rue_maitresse:
#         if gr_rue_maitresse.name != group_area_maitresse.name:
#             hn_maitresse = HouseNumber.select().where(HouseNumber.parent == gr_rue_maitresse)
#             print(gr_rue_maitresse)
#             for hn in hn_maitresse:
#                 hn.ancestors = group_area_maitresse
#                 hn.version += 1
#                 hn.save()
#     for insee in insee_secondaire:
#         print(insee)
#         mun_secondaire = Municipality.get(Municipality.insee == insee)
#         pc_secondaire = PostCode.select().where(PostCode.municipality == mun_secondaire).first()
#         if pc_secondaire is not None:
#             pc_secondaire.municipality = mun_maitresse
#             pc_secondaire.version += 1
#             pc_secondaire.save()
#         group_rue_secondaire=Group.select().where(Group.municipality==mun_secondaire)
#         for group_rue in group_rue_secondaire:
#                 group_rue.municipality=mun_maitresse
#                 group_rue.version+=1
#                 group_rue.save()
