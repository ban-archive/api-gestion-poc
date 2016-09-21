from ban.commands.init import process_row
from ban.core import models
from ban.tests import factories


# File: 01_municipalities.json
def test_process_municipality(session):
    data = {"type": "municipality", "source": "INSEE/COG (2015)",
            "insee": "22059", "name": "Le Fœil"}
    process_row(data)
    assert models.Municipality.select().count() == 1
    municipality = models.Municipality.first()
    assert municipality.name == "Le Fœil"
    assert municipality.insee == "22059"
    assert municipality.attributes['source'] == "INSEE/COG (2015)"


# File: 02_groups.json
def test_process_group(session):
    municipality = factories.MunicipalityFactory(insee="90008")
    data = {"type": "group", "source": "DGFIP/FANTOIR (2015-07)",
            "group": "way", "municipality:insee": "90008",
            "fantoir": "900080203", "name": "GRANDE RUE F. MITTERRAND",
            "attributes": {"somekey": "somevalue"}}
    process_row(data)
    assert models.Group.select().count() == 1
    group = models.Group.first()
    assert group.attributes['source'] == 'DGFIP/FANTOIR (2015-07)'
    assert group.attributes['somekey'] == 'somevalue'
    assert group.kind == models.Group.WAY
    assert group.municipality == municipality
    assert group.fantoir == "900080203"
    assert group.name == "GRANDE RUE F. MITTERRAND"


def test_process_group_do_not_drop_attributes(session):
    group = factories.GroupFactory(fantoir='900080203',
                                   municipality__insee="90008",
                                   attributes={'iwashere': 'before',
                                               'me': 'too'})
    data = {"type": "group", "source": "DGFIP/FANTOIR (2015-07)",
            "group": "way", "municipality:insee": "90008",
            "fantoir": "900080203", "name": "GRANDE RUE F. MITTERRAND",
            "attributes": {"me": "no"}}
    process_row(data)
    assert models.Group.select().count() == 1
    group = models.Group.first()
    assert group.attributes['iwashere'] == 'before'
    assert group.attributes['me'] == 'no'


# File: 03_postcodes.json
def test_process_postcode(session):
    municipality = factories.MunicipalityFactory(insee="01030")
    data = {"type": "postcode", "source": "La Poste (2015)",
            "postcode": "01480", "name": "BEAUREGARD",
            "municipality:insee": "01030"}
    process_row(data)
    assert models.PostCode.select().count() == 1
    postcode = models.PostCode.first()
    assert postcode.code == "01480"
    assert postcode.name == "BEAUREGARD"
    assert postcode.municipality == municipality
    assert postcode.attributes['source'] == "La Poste (2015)"


# File: 03_postcodes.json
def test_process_can_import_two_postcode_with_same_code(session):
    factories.MunicipalityFactory(insee="90049")
    factories.MunicipalityFactory(insee="90050")
    first = {"type": "postcode", "source": "La Poste (2015)",
             "postcode": "90150", "name": "FOUSSEMAGNE",
             "municipality:insee": "90049"}
    second = {"type": "postcode", "source": "La Poste (2015)",
              "postcode": "90150", "name": "FRAIS",
              "municipality:insee": "90050"}
    process_row(first)
    process_row(second)
    assert models.PostCode.select().count() == 2


# File: 04_housenumbers_dgfip.json
def test_process_housenumber_from_dgfip(session):
    group = factories.GroupFactory(fantoir="900010016")
    data = {"type": "housenumber", "source": "DGFiP/BANO (2016-04)",
            "group:fantoir": "900010016", "numero": "15", "ordinal": "bis"}
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.attributes['source'] == "DGFiP/BANO (2016-04)"
    assert housenumber.parent == group
    assert housenumber.number == "15"
    assert housenumber.ordinal == "bis"


def test_process_housenumber_skip_duplicate_cia_on_same_source(session):
    factories.GroupFactory(municipality__insee="78297", fantoir="782970102")
    data1 = {"type": "housenumber", "source": "DGFiP/BANO (2016-04)",
             "group:fantoir": "782970102", "numero": "6", "ordinal": "B"}
    data2 = {"type": "housenumber", "source": "DGFiP/BANO (2016-04)",
             "group:fantoir": "782970102", "numero": "6", "ordinal": "b"}
    process_row(data1)
    process_row(data2)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.ordinal == "B"


def test_process_housenumber_skip_duplicate_cia_on_different_source(session):
    group = factories.GroupFactory(municipality__insee="90001",
                                   fantoir="900010016")
    factories.HouseNumberFactory(parent=group, number="2", ordinal="B",
                                 attributes={"source": "DGFiP"})
    factories.HouseNumberFactory(parent=group, number="2", ordinal="",
                                 attributes={"source": "DGFiP"})

    # There is no ordinal, but the CIA refers to an ordinal, like if the
    # ordinal has been removed. But the housenumber without ordinal already
    # exists in the DB.
    data = {"type": "housenumber", "source": "BAN",
            "cia": "90001_0016_2_B", "group:fantoir": "900010016",
            "numero": "2", "ordinal": ""}
    process_row(data)
    assert models.HouseNumber.select().count() == 2
    housenumber = models.HouseNumber.first(
        models.HouseNumber.cia == "90001_0016_2_B")
    assert housenumber.ordinal == "B"


# File: 05_positions_dgfip.json
def test_process_position_from_dgfip(session):
    data = {"type": "position", "kind": "entrance",
            "source": "DGFiP/BANO (2016-04)",
            "housenumber:cia": "90001_0016_15_bis",
            "geometry": {"type": "Point",
                         "coordinates": [6.87116577514, 47.6029533961]}}
    group = factories.GroupFactory(municipality__insee="90001",
                                   fantoir="900010016")
    housenumber = factories.HouseNumberFactory(parent=group, number="15",
                                               ordinal="bis")
    process_row(data)
    assert models.Position.select().count() == 1
    position = models.Position.first()
    assert position.kind == models.Position.ENTRANCE
    assert position.source == "DGFiP/BANO (2016-04)"
    assert position.housenumber == housenumber
    assert position.center.coords == (6.87116577514, 47.6029533961)


# File: 06x_housenumbers_ban.json
def test_process_housenumber_from_oldban(session):
    data = {"type": "housenumber", "source": "BAN (2016-06-05)",
            "cia": "90001_0005_2_BIS", "group:fantoir": "900010005",
            "numero": "2", "ordinal": "BIS",
            "ign": "ADRNIVX_0000000259416737", "postcode:code": "90400"}
    group = factories.GroupFactory(municipality__insee="90001",
                                   fantoir="900010005")
    factories.HouseNumberFactory(parent=group, number="2", ordinal="bis")
    factories.PostCodeFactory(municipality=group.municipality, code="90400")
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.attributes['source'] == "BAN (2016-06-05)"
    assert housenumber.parent == group
    assert housenumber.number == "2"
    assert housenumber.ordinal == "BIS"
    assert housenumber.postcode.code == "90400"
    assert housenumber.ign == "ADRNIVX_0000000259416737"
    assert len(housenumber.versions) == 2


# File: 07x_positions_ban.json
def test_process_positions_from_oldban(session):
    data = {"type": "position", "kind": "unknown", "name": "Bâtiment A",
            "source": "BAN (2016-06-05)", "housenumber:cia": "90001_0005_5_",
            "ign": "ADRNIVX_0000000259416584",
            "geometry": {"type": "Point",
                         "coordinates": [6.871125, 47.602046]}}
    group = factories.GroupFactory(municipality__insee="90001",
                                   fantoir="900010005")
    housenumber = factories.HouseNumberFactory(parent=group, number="5",
                                               ordinal="")
    process_row(data)
    assert models.Position.select().count() == 1
    position = models.Position.first()
    assert position.kind == models.Position.UNKNOWN
    assert position.source == "BAN (2016-06-05)"
    assert position.housenumber == housenumber
    assert position.center.coords == (6.871125, 47.602046)
    assert position.name == "Bâtiment A"


def test_process_positions_does_not_reset_name_key_if_not_given(session):
    data = {"type": "position", "kind": "entrance",
            "housenumber:cia": "90001_0005_5_",
            "ign": "ADRNIVX_0000000261741380"}
    factories.PositionFactory(
        housenumber__number='5',
        housenumber__ordinal='',
        housenumber__parent__municipality__insee='90001',
        housenumber__parent__fantoir='900010005',
        ign='ADRNIVX_0000000261741380',
        name='Bâtiment A')
    process_row(data)
    position = models.Position.first()
    assert position.name == "Bâtiment A"
    assert position.version == 2


def test_process_positions_reset_name_key_if_null(session):
    data = {"type": "position", "kind": "entrance", "name": None,
            "ign": "ADRNIVX_0000000261741380",
            "housenumber:cia": "90001_0005_5_"}
    factories.PositionFactory(
        housenumber__number='5',
        housenumber__ordinal='',
        housenumber__parent__municipality__insee='90001',
        housenumber__parent__fantoir='900010005',
        ign='ADRNIVX_0000000261741380',
        name='Bâtiment A')
    process_row(data)
    position = models.Position.first()
    assert position.name is None
    assert position.version == 2


def test_can_match_housenumber_parent_from_ign_id(session):
    data = {"type": "housenumber", "source": "IGN (2016-06)",
            "ign": "ADRNIVX_0000000261474435", "group:ign": "06002#003",
            "numero": "70", "ordinal": ""}
    group = factories.GroupFactory(municipality__insee='06002',
                                   fantoir='', ign='06002#003')
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.parent == group
    assert housenumber.ign == 'ADRNIVX_0000000261474435'


def test_can_match_housenumber_parent_from_laposte_id(session):
    data = {"type": "housenumber", "source": "Poste/RAN (2016-06)",
            "numero": None, "group:laposte": "02855657",
            "laposte": "0600222227"}
    group = factories.GroupFactory(municipality__insee='06002',
                                   fantoir='', laposte='02855657')
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.parent == group
    assert housenumber.laposte == '0600222227'


def test_can_update_housenumber_laposte_with_ign_id(session):
    data = {"type": "housenumber", "source": "IGN/Poste (2016-06)",
            "ign": "ADRNIVX_0000000261488312", "laposte": "060012222M"}
    housenumber = factories.HouseNumberFactory(ign='ADRNIVX_0000000261488312')
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.laposte == '060012222M'


def test_can_update_housenumber_with_parent_number_and_ordinal(session):
    data = {"type": "housenumber", "source": "Poste (2016-06)",
            "group:laposte": "00067358", "laposte": "060012223P",
            "numero": "5", "ordinal": "", "postcode:code": "06910",
            "municipality:insee": "06900"}
    postcode = factories.PostCodeFactory(code='06910',
                                         municipality__insee='06900')
    housenumber = factories.HouseNumberFactory(parent__laposte='00067358',
                                               number='5', ordinal='')
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.laposte == '060012223P'
    assert housenumber.postcode == postcode


def test_can_update_housenumber_postcode_with_laposte_id(session):
    data = {"type": "housenumber", "source": "Poste (2016-06)",
            "laposte": "060012223P", "postcode:code": "06910",
            "municipality:insee": "06900"}
    postcode = factories.PostCodeFactory(code='06910',
                                         municipality__insee='06900')
    housenumber = factories.HouseNumberFactory(laposte='060012223P')
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.postcode == postcode


def test_can_match_position_parent_from_ign_id(session):
    data = {"type": "position", "source": "IGN (2016-06)",
            "ign": "XXX",
            "geometry": {"type": "Point",
                         "coordinates": [6.82920162869564, 47.6098351749073]},
            "housenumber:ign": "ADRNIVX_0000000261474435"}
    housenumber = factories.HouseNumberFactory(ign='ADRNIVX_0000000261474435')
    process_row(data)
    assert models.Position.select().count() == 1
    position = models.Position.first()
    assert position.housenumber == housenumber
    assert position.ign == 'XXX'


def test_process_group_without_fantoir_does_not_delete_it(session):
    data = {'ign': '06004#357', 'source': 'IGN/Poste (2016-06)',
            'laposte': '02500921', 'type': 'group'}
    group = factories.GroupFactory(ign="06004#357", fantoir="060042357")
    process_row(data)
    group = models.Group.first()
    assert group.fantoir == '060042357'
    assert group.ign == '06004#357'


def test_can_import_group_with_laposte_but_no_fantoir(session):
    data = {'laposte': '02500934', 'municipality:insee': '06004',
            'type': 'group', 'name': 'VOIE DU TANIT', 'group': 'way',
            'source': 'Poste/RAN (2016-06)'}
    municipality = factories.MunicipalityFactory(insee="06004")
    process_row(data)
    group = models.Group.first()
    assert group.laposte == '02500934'
    assert group.municipality == municipality


# File: 09x_positions_sga-ign.json
def test_process_positions_from_sga_ign(session):
    data = {'type': 'position', 'kind': 'segment',
            'positionning': 'interpolation', 'source': 'IGN (2016-04)',
            'housenumber:cia': '90004_0022_1_',
            'ign': 'ADRNIVX_0000000354868426',
            'geometry': {'type': 'Point',
                         'coordinates': [6.82920162869564, 47.6098351749073]}}
    group = factories.GroupFactory(municipality__insee='90004',
                                   fantoir='900040022')
    housenumber = factories.HouseNumberFactory(parent=group, number='1',
                                               ordinal='')
    process_row(data)
    assert models.Position.select().count() == 1
    position = models.Position.first()
    assert position.kind == models.Position.SEGMENT
    assert position.positioning == models.Position.INTERPOLATION
    assert position.source == 'IGN (2016-04)'
    assert position.ign == 'ADRNIVX_0000000354868426'
    assert position.housenumber == housenumber
    assert position.center.coords == (6.82920162869564, 47.6098351749073)


# File: 09x_positions_sga-ign.json
def test_can_update_position_from_ign_identifier(session):
    data = {'type': 'position', 'kind': 'segment',
            'positionning': 'interpolation', 'source': 'IGN (2016-04)',
            'housenumber:cia': '90004_0022_1_',
            'ign': 'ADRNIVX_0000000354868426',
            'geometry': {'type': 'Point',
                         'coordinates': [6.82920162869564, 47.6098351749073]}}
    housenumber = factories.HouseNumberFactory(
        parent__fantoir='900040022',
        parent__municipality__insee='90004',
        number='1',
        ordinal='')
    position = factories.PositionFactory(ign='ADRNIVX_0000000354868426',
                                         housenumber=housenumber)
    process_row(data)
    assert models.Position.select().count() == 1
    position = models.Position.first()
    assert position.source == 'IGN (2016-04)'
    assert position.housenumber == housenumber


# File: 10_groups-poste-matricule.json
def test_import_poste_group_matricule(session):
    data = {'type': 'group', 'source': 'IGN (2016-04)',
            'fantoir': '330010005', 'laposte': '00580321'}
    factories.GroupFactory(name='RUE DES ARNAUDS', municipality__insee='33001',
                           fantoir='330010005', kind=models.Group.WAY)
    process_row(data)
    assert models.Group.select().count() == 1
    group = models.Group.first()
    assert group.name == 'RUE DES ARNAUDS'
    assert group.laposte == '00580321'
    assert group.attributes['source'] == 'IGN (2016-04)'


# File: 11_housenumbers_group_cea_poste.json
def test_import_housenumbers_group_cea_poste(session):
    data = {'type': 'housenumber', 'source': 'IGN/Poste (2016-04)',
            'group:fantoir': '330010005', 'laposte': '330012223B',
            'numero': None}
    factories.GroupFactory(name='RUE DES ARNAUDS', municipality__insee='33001',
                           fantoir='330010005', kind=models.Group.WAY)
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.number is None
    assert housenumber.ordinal is None
    assert housenumber.laposte == '330012223B'


# File: 12_housenumber_cea.json
def test_import_housenumber_cea(session):
    data = {'type': 'housenumber', 'cia': '33001_B072_2_',
            'laposte': '33001223T2', 'numero': '2', 'ordinal': '',
            'source': 'IGN/Poste (2016-04)', 'group:fantoir': '33001B072'}
    group = factories.GroupFactory(municipality__insee='33001',
                                   fantoir='33001B072', kind=models.Group.AREA)
    factories.HouseNumberFactory(parent=group, number='2', ordinal='')
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.laposte == '33001223T2'


# File: 15_group_noms_cadastre_dgfip_bano.json
def test_import_group_from_bano_dgfip(session):
    data = {'type': 'group', 'source': 'DGFiP/BANO (2016-05)',
            'addressing': 'classical', 'fantoir': '01001A008',
            'name': 'Lotissement Bellevue'}
    factories.GroupFactory(municipality__insee='01001', fantoir='01001A008',
                           kind=models.Group.AREA, name='LOTISSEMENT BELLEVUE')
    process_row(data)
    assert models.Group.select().count() == 1
    group = models.Group.first()
    assert group.name == 'Lotissement Bellevue'
    assert group.addressing == 'classical'
    assert group.version == 2
