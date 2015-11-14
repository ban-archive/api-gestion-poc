from pathlib import Path

from ban.commands.importer import municipalities
from ban.core import models


# Fail with chunksize other than 1
# https://bitbucket.org/pypa/setuptools/issues/443/
def xtest_import_municipalities(staff):
    path = Path(__file__).parent / 'data/municipalities.csv'
    municipalities(path)
    assert len(models.Municipality.select()) == 4


def xtest_import_municipalities_can_be_filtered_by_departement():
    path = Path(__file__).parent / 'data/municipalities.csv'
    municipalities(path, departement=33)
    assert len(models.Municipality.select()) == 1
