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
            "group:fantoir": "90008_0203T", "name": "GRANDE RUE F. MITTERRAND"}
    process_row(data)
    assert models.Group.select().count() == 1
    group = models.Group.first()
    assert group.attributes['source'] == "DGFIP/FANTOIR (2015-07)"
    assert group.kind == models.Group.WAY
    assert group.municipality == municipality
    assert group.fantoir == "900080203"
    assert group.name == "GRANDE RUE F. MITTERRAND"


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
            "ref:ign": "ADRNIVX_0000000259416737", "postcode": "90400"}
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


# File: 07x_positions_ban.json
def test_process_positions_from_oldban(session, reporter):
    data = {"type": "position", "kind": "unknown",
            "source": "BAN (2016-06-05)", "housenumber:cia": "90001_0005_5_",
            "ref:ign": "ADRNIVX_0000000259416584",
            "geometry": {"type": "Point",
                         "coordinates": [6.871125, 47.602046]}}
    group = factories.GroupFactory(municipality__insee="90001",
                                   fantoir="900010005")
    housenumber = factories.HouseNumberFactory(parent=group, number="5",
                                               ordinal="")
    process_row(data)
    print(reporter)
    assert models.Position.select().count() == 1
