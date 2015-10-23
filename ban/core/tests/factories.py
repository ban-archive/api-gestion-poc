import factory
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from factory.fuzzy import FuzzyText

from ban.core import models


class UserFactory(factory.django.DjangoModelFactory):
    username = FuzzyText(length=12)
    password = factory.PostGenerationMethodCall('set_password', 'password')
    email = factory.LazyAttribute(lambda obj: '%s@example.com' % obj.username)

    class Meta:
        model = get_user_model()


class BaseFactory(factory.django.DjangoModelFactory):
    created_by = factory.SubFactory(UserFactory)
    modified_by = factory.SubFactory(UserFactory)


class MunicipalityFactory(BaseFactory):
    name = "Montbrun-Bocage"
    insee = "31365"

    class Meta:
        model = models.Municipality


class LocalityFactory(BaseFactory):
    name = "L'Empereur"
    fantoir = "0080N"
    municipality = factory.SubFactory(MunicipalityFactory)

    class Meta:
        model = models.Locality


class StreetFactory(BaseFactory):
    name = "Rue des Pyrénées"
    fantoir = "0080N"
    municipality = factory.SubFactory(MunicipalityFactory)

    class Meta:
        model = models.Street


class HouseNumberFactory(BaseFactory):
    number = "18"
    ordinal = "bis"
    street = factory.SubFactory(StreetFactory)

    class Meta:
        model = models.HouseNumber


class PositionFactory(BaseFactory):
    center = Point(-1.1111, 48.8888)
    housenumber = factory.SubFactory(HouseNumberFactory)

    class Meta:
        model = models.Position
