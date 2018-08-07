# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_google_maps.fields
import model_utils.fields
import django.utils.timezone
import organizations.base
import organizations.fields
import uuid
import django_loci.storage
import openwisp_users.mixins
from ..models import Location

class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='location',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='openwisp_users.Organization', verbose_name='organization')),
                ('name',models.CharField(max_length=100)),
                ('is_mobile', models.BooleanField(db_index=True, default=False, help_text='is this location a moving object?', verbose_name='is mobile?')),
                ('type', models.CharField(choices=[('outdoor', 'Outdoor environment (eg: street, square, garden, land)'), ('indoor', 'Indoor environment (eg: building, roofs, subway, large vehicles)')], db_index=True, help_text='indoor locations can have floorplans associated to them', max_length=8)),
                ('address', django_google_maps.fields.AddressField(max_length=100,blank=True, null=True,unique=True)),
                ('geolocation', django_google_maps.fields.GeoLocationField(max_length=100,blank=True, null=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FloorPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('floor', models.SmallIntegerField(verbose_name='floor')),
                ('image', models.ImageField(help_text='floor plan image', storage=django_loci.storage.OverwriteStorage(), upload_to=django_loci.storage.OverwriteStorage.upload_to, verbose_name='image')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='openwisp_users.Organization', verbose_name='organization'))
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='floorplan',
            name='location',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='geo.Location'),
        ),
        migrations.CreateModel(
            name='DeviceLocation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('indoor', models.CharField(blank=True, max_length=64, null=True, verbose_name='indoor position')),
                ('content_object', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='config.Device')),
            ],
            options={
                'abstract': False,
            },
            bases=(openwisp_users.mixins.ValidateOrgMixin, models.Model),
        ),
        migrations.AddField(
            model_name='devicelocation',
            name='floorplan',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='geo.FloorPlan'),
        ),
        migrations.AddField(
            model_name='devicelocation',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='geo.Location'),
        ),
    ]
