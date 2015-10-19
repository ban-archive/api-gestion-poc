import re

from django.contrib.gis.db import models
from django.contrib.gis import forms


lonlat_pattern = re.compile('^[\[\(]{1}(?P<lon>\d{,3}(:?\.\d*)?), ?(?P<lat>\d{,3}(\.\d*)?)[\]\)]{1}$')  # noqa
point_template = 'POINT ({} {})'


class HouseNumberFormField(forms.PointField):

    def to_python(self, value):
        # Allow to pass list or tuple as coordinates.
        if isinstance(value, (list, tuple)):
            value = point_template.format(value[0], value[1])
        else:
            search = lonlat_pattern.search(value)
            if search:
                value = point_template.format(search.group('lon'),
                                              search.group('lat'))
        return super().to_python(value)


class HouseNumberField(models.PointField):
    form_class = HouseNumberFormField
