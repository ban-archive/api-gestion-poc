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

    def abort(self, msg):
        self.stderr.write(msg)
        sys.exit(1)

    def skip(self, msg, metadata):
            self.stderr.write(u'⚠ Skipping. {}.'.format(msg))
            for key, value in metadata.items():
                self.stdout.write(u'- {}: {}'.format(key, value))
            self.stdout.write('-' * 20)

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
        path = os.path.abspath(options['path'])
        self.update = options['update']
        if not os.path.exists(path):
            self.abort('Path does not exist: {}'.format(path))
        self.ROOT = os.path.dirname(path)
        rows = self.load(path)
        for row in rows:
            self.add(row)

    def add(self, metadata):
        insee = metadata.get('insee')
        name = metadata.get('nom_com')
        siren = metadata.get('siren_com')

        instance = models.Municipality.objects.filter(insee=insee).first()
        if instance and not self.update:
            return self.skip('Municipality exists. Use --update to reimport '
                             'data', metadata)

        data = dict(
            name=name,
            insee=insee,
            siren=siren,
            version=1,
        )
        form = forms.Municipality(data=data, instance=instance)

        if form.is_valid():
            municipality = form.save()
            self.stdout.write(u'✔ Created {}'.format(municipality))
        else:
            for field, error in form.errors.items():
                self.skip('{}: {}'.format(field, error.as_text()), metadata)
