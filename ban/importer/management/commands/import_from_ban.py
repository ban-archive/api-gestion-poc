import json
import os
import sys

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from ban.core import models, forms


class Command(BaseCommand):
    help = ('Import BAN data from http://bano.openstreetmap.fr/BAN_odbl/')

    def add_arguments(self, parser):
        parser.add_argument('path', help='Path to JSON stream.')
        parser.add_argument('--update', action='store_true', default=False,
                            help='Update instance when data with same '
                                 'identifier already exists.')

    def abort(self, msg):
        self.stderr.write(msg)
        sys.exit(1)

    def skip(self, msg, metadata):
            self.skipped.append((msg, metadata))

    def render_results(self):
        if self.skipped and self.verbose:
            self.stdout.write('******* SKIPPED ********')
            for msg, metadata in self.skipped:
                self.stderr.write(u'⚠ Skipped. {}.'.format(msg))
                for key, value in metadata.items():
                    self.stdout.write(u'- {}: {}'.format(key, value))
                self.stdout.write('-' * 20)
        self.stdout.write('Processed: {}'.format(self.processed))
        self.stdout.write('Imported streets: {}'.format(self.imported_streets))
        self.stdout.write('Imported housenumbers: {}'.format(self.imported_housenumbers))  # noqa
        self.stdout.write('Imported positions: {}'.format(self.imported_positions))  # noqa
        self.stdout.write('Skipped items (run with --verbosity 1 to get details): {}'.format(len(self.skipped)))  # noqa
        self.stdout.write('-' * 40)

    def handle(self, *args, **options):
        self.verbose = options['verbosity'] > 1
        self.imported_positions = 0
        self.imported_housenumbers = 0
        self.imported_streets = 0
        self.processed = 0
        self.skipped = []
        path = os.path.abspath(options['path'])
        self.update = options['update']
        if not os.path.exists(path):
            self.abort('Path does not exist: {}'.format(path))
        self.ROOT = os.path.dirname(path)
        with Path(path).open() as f:
            self.stdout.write('Started!')
            for row in f:
                if not row:
                    continue
                self.process_row(json.loads(row))
                self.processed += 1
                if self.processed % 100 == 0:
                    self.render_results()
        self.render_results()

    def process_row(self, metadata):
        name = metadata.get('name')
        id = metadata.get('id')
        insee = metadata.get('citycode')
        fantoir = ''.join(id.split('_')[:2])

        instance = models.Street.objects.filter(fantoir=fantoir).first()
        if instance and not self.update:
            return self.skip('Street exists. Use --update to reimport '
                             'data', metadata)

        municipality = models.Municipality.objects.filter(insee=insee).first()
        data = dict(
            name=name,
            fantoir=fantoir,
            municipality=municipality.pk,
            version=1,
        )
        form = forms.Street(data=data, instance=instance)

        if form.is_valid():
            street = form.save()
            self.imported_streets += 1
            housenumbers = metadata.get('housenumbers')
            if housenumbers:
                self.add_housenumbers(street, housenumbers)
        else:
            for field, error in form.errors.items():
                self.skip('{}: {}'.format(field, error.as_text()), metadata)

    def add_housenumbers(self, street, housenumbers):
        for id, metadata in housenumbers.items():
            self.add_housenumber(street, id, metadata)

    def add_housenumber(self, street, id, metadata):
        number, *ordinal = id.split(' ')
        ordinal = ordinal[0] if ordinal else ''
        center = [metadata['lon'], metadata['lat']]
        data = dict(
            number=number,
            ordinal=ordinal,
            street=street.pk,
            version=1
        )
        form = forms.HouseNumber(data=data)

        if form.is_valid():
            housenumber = form.save()
            form = forms.Position(data=dict(center=center, version=1,
                                            housenumber=housenumber.pk))
            self.imported_housenumbers += 1
            if form.is_valid():
                form.save()
                self.imported_positions += 1
        else:
            for field, error in form.errors.items():
                self.skip('{}: {}'.format(field, error.as_text()), metadata)
