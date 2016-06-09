from ban.commands.init import process_row
from ban.core import models
from ban.tests import factories


def test_process_municipality(session):
    data = {"type": "municipality", "source": "INSEE/COG (2015)",
            "insee": "22059", "name": "Le Fœil"}
    process_row(data)
    assert models.Municipality.select().count() == 1
    municipality = models.Municipality.first()
    assert municipality.name == "Le Fœil"
    assert municipality.insee == "22059"
    assert municipality.attributes['source'] == "INSEE/COG (2015)"


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


def test_process_housenumber_from_dgfip(session):
    municipality = factories.MunicipalityFactory(insee="01030")
    group = factories.GroupFactory(municipality=municipality,
                                   fantoir="900010016")
    data = {"type": "housenumber", "source": "DGFiP/BANO (2016-04)",
            "group:fantoir": "90001_0016V", "numero": "15", "ordinal": "bis"}
    process_row(data)
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.attributes['source'] == "DGFiP/BANO (2016-04)"
    assert housenumber.parent == group
    assert housenumber.number == "15"
    assert housenumber.ordinal == "bis"
