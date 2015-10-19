# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import ban.core.fields
import django.utils.timezone
from django.conf import settings
import django.contrib.auth.models
import django.core.validators
import ban.core.models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('password', models.CharField(verbose_name='password', max_length=128)),
                ('last_login', models.DateTimeField(null=True, blank=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status', default=False)),
                ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')], verbose_name='username', max_length=30, unique=True, error_messages={'unique': 'A user with that username already exists.'})),
                ('first_name', models.CharField(blank=True, verbose_name='first name', max_length=30)),
                ('last_name', models.CharField(blank=True, verbose_name='last name', max_length=30)),
                ('email', models.EmailField(blank=True, verbose_name='email address', max_length=254)),
                ('is_staff', models.BooleanField(help_text='Designates whether the user can log into this admin site.', verbose_name='staff status', default=False)),
                ('is_active', models.BooleanField(help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active', default=True)),
                ('date_joined', models.DateTimeField(verbose_name='date joined', default=django.utils.timezone.now)),
                ('company', models.CharField(blank=True, verbose_name='Company', max_length=100)),
                ('groups', models.ManyToManyField(help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', blank=True, verbose_name='groups', related_query_name='user', related_name='user_set', to='auth.Group')),
                ('user_permissions', models.ManyToManyField(help_text='Specific permissions for this user.', blank=True, verbose_name='user permissions', related_query_name='user', related_name='user_set', to='auth.Permission')),
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
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('number', models.CharField(max_length=16)),
                ('ordinal', models.CharField(blank=True, max_length=16)),
                ('cia', models.CharField(blank=True, max_length=100)),
                ('created_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True, related_name='housenumber_created')),
            ],
            bases=(models.Model, ban.core.models.PublicMixin),
        ),
        migrations.CreateModel(
            name='Locality',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(verbose_name='name', max_length=200)),
                ('fantoir', models.CharField(null=True, blank=True, max_length=5)),
                ('created_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True, related_name='locality_created')),
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
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(verbose_name='name', max_length=200)),
                ('insee', models.CharField(max_length=5)),
                ('siren', models.CharField(max_length=9)),
                ('created_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True, related_name='municipality_created')),
                ('modified_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'abstract': False,
                'ordering': ('name',),
            },
            bases=(models.Model, ban.core.models.PublicMixin),
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('center', ban.core.fields.HouseNumberField(geography=True, verbose_name='center', srid=4326)),
                ('source', models.CharField(blank=True, max_length=64)),
                ('comment', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True, related_name='position_created')),
                ('housenumber', models.ForeignKey(to='core.HouseNumber')),
                ('modified_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            bases=(models.Model, ban.core.models.PublicMixin),
        ),
        migrations.CreateModel(
            name='Street',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('version', models.SmallIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(verbose_name='name', max_length=200)),
                ('fantoir', models.CharField(null=True, blank=True, max_length=5)),
                ('created_by', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True, related_name='street_created')),
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
            field=models.ForeignKey(blank=True, null=True, to='core.Locality'),
        ),
        migrations.AddField(
            model_name='housenumber',
            name='modified_by',
            field=models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, null=True),
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
