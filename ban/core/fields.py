import re

import peewee

lonlat_pattern = re.compile('^[\[\(]{1}(?P<lon>\d{,3}(:?\.\d*)?), ?(?P<lat>\d{,3}(\.\d*)?)[\]\)]{1}$')  # noqa
point_template = 'POINT ({} {})'

# https://github.com/MAPC/rental-listing-aggregator/blob/09d3d8d75ea3697431dd080f49c4fc1f28a83263/.ipynb_checkpoints/Untitled-checkpoint.ipynb
# https://github.com/mima3/estat/blob/537689ad4ebc96af34e1c66a9997241fa847d8c1/estat_db.py
# https://github.com/ryanj/flask-postGIS/blob/master/map.py
# http://chrishaganreporting.com/2014/03/inserting-geometry-with-postgis-and-psycopg2/
# http://stackoverflow.com/questions/14940285/using-postgis-on-python-3
# http://stackoverflow.com/questions/29888040/how-to-join-on-spatial-functions-in-peewee


class HouseNumberField(peewee.Field):
    db_field = 'point'

    def db_value(self, value):
        return 'POINT (1, 2)'
        print("VALUE", value)
        return str(value)

    def python_value(self, value):
        return 'POINT (3, 4)'
    #     # Allow to pass list or tuple as coordinates.
    #     if isinstance(value, (list, tuple)):
    #         value = point_template.format(value[0], value[1])
    #     elif value is not None:
    #         search = lonlat_pattern.search(value)
    #         if search:
    #             value = point_template.format(search.group('lon'),
    #                                           search.group('lat'))
    #     return value

peewee.PostgresqlDatabase.register_fields({'uuid': 'uuid'})
peewee.SqliteDatabase.register_fields({'uuid': 'uuid'})
