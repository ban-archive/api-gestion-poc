from django.forms import ModelForm

from . import models


class Position(ModelForm):

    class Meta:
        fields = '__all__'
        model = models.Position


class HouseNumber(ModelForm):

    class Meta:
        fields = '__all__'
        model = models.HouseNumber


class Street(ModelForm):

    class Meta:
        fields = '__all__'
        model = models.Street


class Locality(ModelForm):

    class Meta:
        fields = '__all__'
        model = models.Locality


class Municipality(ModelForm):

    class Meta:
        fields = '__all__'
        model = models.Municipality
