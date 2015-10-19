import factory
from factory.fuzzy import FuzzyText
from django.contrib.gis.geos import Point
from django.contrib.auth import get_user_model

from ban.core.models import HouseNumber, Municipality, Position, Street


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
        model = Municipality


class StreetFactory(BaseFactory):
    name = "Rue des Pyrénées"
    fantoir = "0080N"
    municipality = factory.SubFactory(MunicipalityFactory)

    class Meta:
        model = Street


class HouseNumberFactory(BaseFactory):
    number = "18"
    ordinal = "bis"
    street = factory.SubFactory(StreetFactory)

    class Meta:
        model = HouseNumber


class PositionFactory(BaseFactory):
    center = Point(-1.1111, 48.8888)
    housenumber = factory.SubFactory(HouseNumberFactory)

    class Meta:
        model = Position
