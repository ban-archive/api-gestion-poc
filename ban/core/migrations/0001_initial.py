# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import ban.core.models
import django.utils.timezone
import django.core.validators
from django.conf import settings
import django.contrib.auth.models
import ban.core.fields


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('password', models.CharField(verbose_name='password', max_length=128)),
                ('last_login', models.DateTimeField(verbose_name='last login', blank=True, null=True)),
                ('is_superuser', models.BooleanField(help_text='Designates that this user has all permissions without explicitly assigning them.', default=False, verbose_name='superuser status')),
                ('username', models.CharField(validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')], error_messages={'unique': 'A user with that username already exists.'}, max_length=30, verbose_name='username', help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True)),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(help_text='Designates whether the user can log into this admin site.', default=False, verbose_name='staff status')),
                ('is_active', models.BooleanField(help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', default=True, verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('company', models.CharField(max_length=100, verbose_name='Company', blank=True)),
                ('groups', models.ManyToManyField(related_name='user_set', blank=True, related_query_name='user', verbose_name='groups', help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', to='auth.Group')),
                ('user_permissions', models.ManyToManyField(related_name='user_set', blank=True, related_query_name='user', verbose_name='user permissions', help_text='Specific permissions for this user.', to='auth.Permission')),
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
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('number', models.CharField(max_length=16)),
                ('ordinal', models.CharField(max_length=16, blank=True)),
                ('cia', models.CharField(max_length=100, blank=True, editable=False)),
                ('created_by', models.ForeignKey(related_name='housenumber_created', editable=False, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            bases=(models.Model, ban.core.models.PublicMixin),
        ),
        migrations.CreateModel(
            name='Locality',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(verbose_name='name', max_length=200)),
                ('fantoir', models.CharField(max_length=9, blank=True, null=True)),
                ('created_by', models.ForeignKey(related_name='locality_created', editable=False, to=settings.AUTH_USER_MODEL, null=True)),
                ('modified_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, ban.core.models.PublicMixin),
        ),
        migrations.CreateModel(
            name='Municipality',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(verbose_name='name', max_length=200)),
                ('insee', models.CharField(max_length=5)),
                ('siren', models.CharField(max_length=9)),
                ('created_by', models.ForeignKey(related_name='municipality_created', editable=False, to=settings.AUTH_USER_MODEL, null=True)),
                ('modified_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('name',),
                'abstract': False,
            },
            bases=(models.Model, ban.core.models.PublicMixin),
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('center', ban.core.fields.HouseNumberField(srid=4326, verbose_name='center', geography=True)),
                ('source', models.CharField(max_length=64, blank=True)),
                ('comment', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(related_name='position_created', editable=False, to=settings.AUTH_USER_MODEL, null=True)),
                ('housenumber', models.ForeignKey(to='core.HouseNumber')),
                ('modified_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            bases=(models.Model, ban.core.models.PublicMixin),
        ),
        migrations.CreateModel(
            name='Street',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(verbose_name='name', max_length=200)),
                ('fantoir', models.CharField(max_length=9, blank=True, null=True)),
                ('created_by', models.ForeignKey(related_name='street_created', editable=False, to=settings.AUTH_USER_MODEL, null=True)),
                ('modified_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True)),
                ('municipality', models.ForeignKey(to='core.Municipality')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, ban.core.models.PublicMixin),
        ),
        migrations.AddField(
            model_name='locality',
            name='municipality',
            field=models.ForeignKey(to='core.Municipality'),
        ),
        migrations.AddField(
            model_name='housenumber',
            name='locality',
            field=models.ForeignKey(blank=True, to='core.Locality', null=True),
        ),
        migrations.AddField(
            model_name='housenumber',
            name='modified_by',
            field=models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='housenumber',
            name='street',
            field=models.ForeignKey(blank=True, to='core.Street', null=True),
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
