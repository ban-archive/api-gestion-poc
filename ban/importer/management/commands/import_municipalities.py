# -*- coding: utf-8 -*-
import csv
import os
import sys

from django.conf import settings
from django.core.management.base import BaseCommand

from ban.core import models, forms


class Command(BaseCommand):
    help = ('Import municipalities from http://www.collectivites-locales.gouv.fr/files/files/epcicom2015.csv.')

    def add_arguments(self, parser):
        parser.add_argument('path', help='Path to CSV metadata.')
        parser.add_argument('--update', action='store_true', default=False,
                            help='Update instance when municipality with same '
                                 'INSEE already exists.')
        parser.add_argument('--departement',
                            help='Only important this departement number. '
                                 'Useful for dev.')

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
        self.stdout.write('Imported: {}'.format(self.imported))
        self.stdout.write('Skipped (run with --verbosity 1 to get details): {}'.format(len(self.skipped)))  # noqa

    def load(self, path):
        with open(path, 'r', encoding='latin1') as f:
            extract = f.read(4096)
            try:
                dialect = csv.Sniffer().sniff(extract)
            except csv.Error:
                dialect = csv.unix_dialect()
            f.seek(0)
            content = f.read()
            return csv.DictReader(content.splitlines(),
                                  dialect=dialect)

    def handle(self, *args, **options):
        self.departement = options['departement']
        self.verbose = options['verbosity'] > 1
        self.imported = 0
        self.processed = 0
        self.skipped = []
        path = os.path.abspath(options['path'])
        self.update = options['update']
        if not os.path.exists(path):
            self.abort('Path does not exist: {}'.format(path))
        self.ROOT = os.path.dirname(path)
        rows = self.load(path)
        self.stdout.write('Started!')
        for row in rows:
            if self.departement and row['dep_epci'] != self.departement:
                continue
            self.add(row)
            self.processed += 1
            if self.processed % 1000 == 0:
                self.stdout.write('Processed: {}'.format(self.processed))
        self.render_results()

    def add(self, metadata):
        insee = metadata.get('insee')
        name = metadata.get('nom_com')
        siren = metadata.get('siren_com')

        instance = models.Municipality.objects.filter(insee=insee).first()
        if instance and not self.update:
            return self.skip('Municipality exists. Use --update to reimport '
                             'data', metadata)

        data = dict(name=name, insee=insee, siren=siren, version=1)
        form = forms.Municipality(data=data, instance=instance)

        if form.is_valid():
            form.save()
            self.imported += 1
        else:
            for field, error in form.errors.items():
                self.skip('{}: {}'.format(field, error.as_text()), metadata)
