# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Version',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('model', models.CharField(max_length=64)),
                ('model_id', models.IntegerField()),
                ('sequential', models.SmallIntegerField()),
                ('data', models.BinaryField()),
            ],
        ),
    ]
