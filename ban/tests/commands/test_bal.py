import codecs
from io import StringIO
from pathlib import Path

from ban.commands.bal import bal
from ban.core import models
from ban.tests import factories


def test_bal_should_create_groups(staff):
    municipality = factories.MunicipalityFactory(name="Acigné", insee="35001")
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0005_99999,,Mail Anita Conti,99999,,Acigné,,,,,,Rennes Métropole,2016-02-22
"""
    bal(StringIO(content))
    assert models.Group.select().count() == 1
    group = models.Group.select().first()
    assert group.name == "Mail Anita Conti"
    assert group.fantoir == "350010005"
    assert group.municipality == municipality
    # No lat/long, so not housenumber should have been created.
    assert models.HouseNumber.select().count() == 0


def test_bal_should_accept_BOM(staff):
    path = Path(__file__).parent / 'data/balwithbom.csv'
    municipality = factories.MunicipalityFactory(name="Acigné", insee="35001")
    with path.open(mode='wb') as f:
        f.write(codecs.BOM_UTF8)
        f.write("""cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0005_99999,,Mail Anita Conti,99999,,Acigné,,,,,,Rennes Métropole,2016-02-22""".encode('utf-8'))
    bal(path)
    assert models.Group.select().count() == 1
    group = models.Group.select().first()
    assert group.name == "Mail Anita Conti"
    assert group.fantoir == "350010005"
    assert group.municipality == municipality
    # No lat/long, so not housenumber should have been created.
    assert models.HouseNumber.select().count() == 0


def test_bal_should_update_group_by_fantoir(staff):
    municipality = factories.MunicipalityFactory(name="Acigné", insee="35001")
    group = factories.GroupFactory(municipality=municipality,
                                   name="Mail Anti Conto", fantoir="350010005")
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0005_99999,,Mail Anita Conti,99999,,Acigné,,,,,,Rennes Métropole,2016-02-22
"""
    bal(StringIO(content))
    assert models.Group.select().count() == 1
    group = models.Group.select().first()
    assert group.name == "Mail Anita Conti"


def test_bal_should_update_group_by_id(staff):
    municipality = factories.MunicipalityFactory(name="Acigné", insee="35001")
    group = factories.GroupFactory(municipality=municipality,
                                   name="Mail Anti Conto")
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0005_99999,{id},Mail Anita Conti,99999,,Acigné,,,,,,Rennes Métropole,2016-02-22
"""
    content = content.format(id=group.id)
    bal(StringIO(content))
    assert models.Group.select().count() == 1
    group = models.Group.select().first()
    assert group.name == "Mail Anita Conti"
    assert group.version == 2


def test_bal_should_create_group_housenumber_and_position_if_latlong(staff):
    factories.MunicipalityFactory(name="Grenoble", insee="38185")
    content = """cle_interop;uid_adresse;voie_nom;numero;suffixe;commune_nom;position;x;y;long;lat;source;date_der_maj\n
38185_0172_99999;;Esplanade Alain Le Ray;99999;;Grenoble;délivrance postale;914027.84;6457539.01;5.72559773087959;45.1839130425293;Ville de Grenoble;2010-12-21
"""
    bal(StringIO(content))
    assert models.Group.select().count() == 1
    group = models.Group.first()
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.parent == group
    assert housenumber.number is None
    assert models.Position.select().count() == 1
    position = models.Position.first()
    assert position.housenumber == housenumber
    assert position.center == (5.72559773087959, 45.1839130425293)


def test_bal_should_create_housenumber_and_position_when_updating_group(staff):
    group = factories.GroupFactory(municipality__insee="38185",
                                   name="Esplanade Alain Le Ray",
                                   fantoir="381850172")
    content = """cle_interop;uid_adresse;voie_nom;numero;suffixe;commune_nom;position;x;y;long;lat;source;date_der_maj\n
38185_0172_99999;;Esplanade Alain Le Ray;99999;;Grenoble;délivrance postale;914027.84;6457539.01;5.72559773087959;45.1839130425293;Ville de Grenoble;2010-12-21
"""
    bal(StringIO(content))
    assert models.Group.select().count() == 1
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.parent == group
    assert housenumber.number is None
    assert models.Position.select().count() == 1
    position = models.Position.first()
    assert position.housenumber == housenumber
    assert position.center == (5.72559773087959, 45.1839130425293)


def test_bal_should_update_housenumber_when_updating_group(staff):
    group = factories.GroupFactory(municipality__insee="38185",
                                   name="Esplanade Alain Le Ray",
                                   fantoir="381850172")
    housenumber = factories.HouseNumberFactory(number=None, parent=group,
                                               ordinal=None, cia='38185_0172_99999')
    content = """cle_interop;uid_adresse;voie_nom;numero;suffixe;commune_nom;position;x;y;long;lat;source;date_der_maj\n
38185_0172_99999;;Esplanade Alain Le Ray;99999;;Grenoble;délivrance postale;914027.84;6457539.01;5.72559773087959;45.1839130425293;Ville de Grenoble;2010-12-21
"""
    bal(StringIO(content))
    assert models.Group.select().count() == 1
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.parent == group
    assert housenumber.number is None
    assert models.Position.select().count() == 1
    position = models.Position.first()
    assert position.housenumber == housenumber
    assert position.center == (5.72559773087959, 45.1839130425293)


def test_bal_should_update_position_when_updating_group(staff):
    group = factories.GroupFactory(municipality__insee="38185",
                                   name="Esplanade Alain Le Ray",
                                   fantoir="381850172")
    housenumber = factories.HouseNumberFactory(number=None, parent=group,
                                               ordinal=None,
                                               cia="38185_0172_99999")
    old_position = factories.PositionFactory(housenumber=housenumber,
                                             kind=models.Position.POSTAL)
    content = """cle_interop;uid_adresse;voie_nom;numero;suffixe;commune_nom;position;x;y;long;lat;source;date_der_maj\n
38185_0172_99999;;Esplanade Alain Le Ray;99999;;Grenoble;délivrance postale;914027.84;6457539.01;5.72559773087959;45.1839130425293;Ville de Grenoble;2010-12-21
"""
    bal(StringIO(content))
    assert models.Group.select().count() == 1
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.first()
    assert housenumber.parent == group
    assert housenumber.number is None
    assert models.Position.select().count() == 1
    position = models.Position.first()
    assert old_position.id == position.id
    assert position.housenumber == housenumber
    assert position.center == (5.72559773087959, 45.1839130425293)


def test_bal_should_create_housenumber(staff):
    municipality = factories.MunicipalityFactory(name="Acigné", insee="35001")
    group = factories.GroupFactory(municipality=municipality,
                                   name="Square Ella Maillart",
                                   fantoir="350010010")
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0010_00001,,Square Ella Maillart,1,,Acigné,bâtiment,,,,,Rennes Métropole,2013-10-23
"""
    bal(StringIO(content))
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.select().first()
    assert housenumber.number == "1"
    assert housenumber.parent == group


def test_bal_should_update_housenumber_by_id(staff):
    housenumber = factories.HouseNumberFactory(number="1")
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0010_00001,{id},Square Ella Maillart,1,,Acigné,bâtiment,,,,,Rennes Métropole,2013-10-23
"""
    content = content.format(id=housenumber.id)
    bal(StringIO(content))
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.select().first()
    assert housenumber.number == "1"
    assert housenumber.version == 2


def test_bal_should_update_housenumber_by_cia(staff):
    group = factories.GroupFactory(name="Square Ella Maillart",
                                   municipality__insee="35001",
                                   fantoir="350010010")
    housenumber = factories.HouseNumberFactory(number="1", parent=group,
                                               ordinal=None)
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0010_00001,,Square Ella Maillart,1,,Acigné,bâtiment,,,,,Rennes Métropole,2013-10-23
"""
    bal(StringIO(content))
    assert models.HouseNumber.select().count() == 1
    housenumber = models.HouseNumber.select().first()
    assert housenumber.number == "1"
    assert housenumber.version == 2


def test_bal_should_create_position_if_xy_are_set(staff):
    municipality = factories.MunicipalityFactory(name="Acigné", insee="35001")
    factories.GroupFactory(municipality=municipality,
                           name="Square Ella Maillart",
                           fantoir="350010010")
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0010_00001,,Square Ella Maillart,1,,Acigné,bâtiment,363371.73430419,6791798.91601974,-1.52808691540987,48.1396656060165,Rennes Métropole,2013-10-23
"""
    bal(StringIO(content))
    assert models.Position.select().count() == 1
    position = models.Position.select().first()
    assert position.center == (-1.52808691540987, 48.1396656060165)


def test_bal_should_add_position_to_existing_housenumber(staff):
    group = factories.GroupFactory(municipality__insee="35001",
                                   name="Square Ella Maillart",
                                   fantoir="350010010")
    housenumber = factories.HouseNumberFactory(number="1", parent=group,
                                               ordinal=None)
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0010_00001,,Square Ella Maillart,1,,Acigné,bâtiment,363371.73430419,6791798.91601974,-1.52808691540987,48.1396656060165,Rennes Métropole,2013-10-23
"""
    bal(StringIO(content))
    assert models.Position.select().count() == 1
    position = models.Position.select().first()
    assert position.center == (-1.52808691540987, 48.1396656060165)
    position.housenumber == housenumber


def test_bal_should_update_position_of_same_kind(staff):
    group = factories.GroupFactory(municipality__insee="35001",
                                   name="Square Ella Maillart",
                                   fantoir="350010010")
    housenumber = factories.HouseNumberFactory(number="1", parent=group,
                                               ordinal=None)
    old_position = factories.PositionFactory(housenumber=housenumber,
                                             kind=models.Position.BUILDING)
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0010_00001,,Square Ella Maillart,1,,Acigné,bâtiment,363371.73430419,6791798.91601974,-1.52808691540987,48.1396656060165,Rennes Métropole,2013-10-23
"""
    bal(StringIO(content))
    assert models.Position.select().count() == 1
    position = models.Position.select().first()
    assert position.id == old_position.id
    assert position.center == (-1.52808691540987, 48.1396656060165)
    position.housenumber == housenumber


def test_bal_should_create_position_if_kind_does_not_exist(staff):
    group = factories.GroupFactory(municipality__insee="35001",
                                   name="Square Ella Maillart",
                                   fantoir="350010010")
    housenumber = factories.HouseNumberFactory(number="1", parent=group,
                                               ordinal=None)
    old_position = factories.PositionFactory(housenumber=housenumber,
                                             kind=models.Position.ENTRANCE)
    content = """cle_interop,uid_adresse,voie_nom,numero,suffixe,commune_nom,position,x,y,long,lat,source,date_der_maj\n
35001_0010_00001,,Square Ella Maillart,1,,Acigné,bâtiment,363371.73430419,6791798.91601974,-1.52808691540987,48.1396656060165,Rennes Métropole,2013-10-23
"""
    bal(StringIO(content))
    assert models.Position.select().count() == 2
    position = models.Position.select().order_by(
                                            models.Position.pk.desc()).first()
    assert position.id != old_position.id
    assert position.center == (-1.52808691540987, 48.1396656060165)
    position.housenumber == housenumber
    old_position.housenumber == housenumber
