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
