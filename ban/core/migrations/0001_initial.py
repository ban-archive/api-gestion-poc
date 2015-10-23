# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import ban.core.fields
import django.contrib.postgres.fields.hstore
import django.contrib.auth.models
import django.core.validators
import django.utils.timezone
from django.conf import settings
from django.contrib.postgres.operations import HStoreExtension

class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        HStoreExtension(),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(help_text='Designates that this user has all permissions without explicitly assigning them.', default=False, verbose_name='superuser status')),
                ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, verbose_name='username', error_messages={'unique': 'A user with that username already exists.'}, validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')], max_length=30)),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=30, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(help_text='Designates whether the user can log into this admin site.', default=False, verbose_name='staff status')),
                ('is_active', models.BooleanField(help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', default=True, verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('company', models.CharField(blank=True, max_length=100, verbose_name='Company')),
                ('groups', models.ManyToManyField(help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', to='auth.Group', related_name='user_set', verbose_name='groups', related_query_name='user', blank=True)),
                ('user_permissions', models.ManyToManyField(help_text='Specific permissions for this user.', to='auth.Permission', related_name='user_set', verbose_name='user permissions', related_query_name='user', blank=True)),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='HouseNumber',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('number', models.CharField(max_length=16)),
                ('ordinal', models.CharField(blank=True, max_length=16)),
                ('cia', models.CharField(blank=True, max_length=100, editable=False)),
                ('created_by', models.ForeignKey(related_name='housenumber_created', null=True, editable=False, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Locality',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('fantoir', models.CharField(blank=True, null=True, max_length=9)),
                ('created_by', models.ForeignKey(related_name='locality_created', null=True, editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(null=True, editable=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Municipality',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('insee', models.CharField(max_length=5)),
                ('siren', models.CharField(max_length=9)),
                ('created_by', models.ForeignKey(related_name='municipality_created', null=True, editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(null=True, editable=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('center', ban.core.fields.HouseNumberField(srid=4326, geography=True, verbose_name='center')),
                ('source', models.CharField(blank=True, max_length=64)),
                ('kind', models.CharField(blank=True, max_length=64)),
                ('attributes', django.contrib.postgres.fields.hstore.HStoreField(blank=True, null=True)),
                ('comment', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(related_name='position_created', null=True, editable=False, to=settings.AUTH_USER_MODEL)),
                ('housenumber', models.ForeignKey(to='core.HouseNumber')),
                ('modified_by', models.ForeignKey(null=True, editable=False, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Street',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('fantoir', models.CharField(blank=True, null=True, max_length=9)),
                ('created_by', models.ForeignKey(related_name='street_created', null=True, editable=False, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(null=True, editable=False, to=settings.AUTH_USER_MODEL)),
                ('municipality', models.ForeignKey(to='core.Municipality')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='locality',
            name='municipality',
            field=models.ForeignKey(to='core.Municipality'),
        ),
        migrations.AddField(
            model_name='housenumber',
            name='locality',
            field=models.ForeignKey(blank=True, null=True, to='core.Locality'),
        ),
        migrations.AddField(
            model_name='housenumber',
            name='modified_by',
            field=models.ForeignKey(null=True, editable=False, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='housenumber',
            name='street',
            field=models.ForeignKey(blank=True, null=True, to='core.Street'),
        ),
        migrations.AlterUniqueTogether(
            name='position',
            unique_together=set([('housenumber', 'source')]),
        ),
        migrations.AlterUniqueTogether(
            name='housenumber',
            unique_together=set([('number', 'ordinal', 'street', 'locality')]),
        ),
    ]
