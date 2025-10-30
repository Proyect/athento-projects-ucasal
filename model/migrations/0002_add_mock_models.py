# -*- coding: utf-8 -*-
# Generated manually for mock models

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('model', '0001_initial'),
    ]

    operations = [
        # Crear modelos nuevos
        migrations.CreateModel(
            name='Team',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('label', models.CharField(default='', max_length=200)),
            ],
            options={
                'verbose_name': 'Team',
                'verbose_name_plural': 'Teams',
                'db_table': 'team_team',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Doctype',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50, unique=True)),
                ('label', models.CharField(default='', max_length=100)),
            ],
            options={
                'verbose_name': 'Doctype',
                'verbose_name_plural': 'Doctypes',
                'db_table': 'doctype_doctype',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='LifeCycleState',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('maximum_time', models.IntegerField(blank=True, help_text='SLA en minutos', null=True)),
            ],
            options={
                'verbose_name': 'Lifecycle State',
                'verbose_name_plural': 'Lifecycle States',
                'db_table': 'lifecycle_state',
                'managed': True,
            },
        ),
        migrations.CreateModel(
            name='Serie',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('label', models.CharField(default='', max_length=200)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='serie_set', to='model.team')),
            ],
            options={
                'verbose_name': 'Serie',
                'verbose_name_plural': 'Series',
                'db_table': 'series_serie',
                'managed': True,
            },
        ),
        # Agregar campos nuevos a File (sin renombrar los existentes)
        migrations.AddField(
            model_name='file',
            name='doctype_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='files', to='model.doctype', db_column='doctype_id'),
        ),
        migrations.AddField(
            model_name='file',
            name='life_cycle_state_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='files', to='model.lifecyclestate', db_column='life_cycle_state_id'),
        ),
        migrations.AddField(
            model_name='file',
            name='serie',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='files', to='model.serie', db_column='serie_id'),
        ),
        # Renombrar campos existentes
        migrations.RenameField(
            model_name='file',
            old_name='doctype',
            new_name='doctype_legacy',
        ),
        migrations.RenameField(
            model_name='file',
            old_name='life_cycle_state',
            new_name='life_cycle_state_legacy',
        ),
        # Agregar campos de cache
        migrations.AddField(
            model_name='file',
            name='_metadata_cache',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AddField(
            model_name='file',
            name='_features_cache',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AddField(
            model_name='file',
            name='life_cycle_state_date',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='file',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='file',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]

