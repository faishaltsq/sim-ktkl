import django.db.models.deletion
from django.db import migrations, models

DEFAULT_PROFESI = [
    'ATLM', 'Radiografer', 'Fisioterapis', 'Nutrisionis',
    'Perekam Medis', 'Apoteker', 'Sanitarian', 'Lainnya',
]


def seed_profesi_and_migrate_data(apps, schema_editor):
    Profesi = apps.get_model('nakes', 'Profesi')
    Nakes = apps.get_model('nakes', 'Nakes')

    profesi_cache = {}
    for nama in DEFAULT_PROFESI:
        obj, _ = Profesi.objects.get_or_create(nama=nama)
        profesi_cache[nama.lower()] = obj

    for nakes in Nakes.objects.all():
        old_val = nakes.profesi_old or ''
        matched = profesi_cache.get(old_val.strip().lower())
        if not matched:
            matched, _ = Profesi.objects.get_or_create(nama=old_val.strip() or 'Lainnya')
            profesi_cache[old_val.strip().lower()] = matched
        nakes.profesi_fk = matched
        nakes.save(update_fields=['profesi_fk'])


class Migration(migrations.Migration):

    dependencies = [
        ('nakes', '0002_dokumenumum'),
    ]

    operations = [
        migrations.CreateModel(
            name='Profesi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama', models.CharField(max_length=100, unique=True)),
            ],
            options={
                'verbose_name': 'Profesi',
                'verbose_name_plural': 'Profesi',
                'ordering': ['nama'],
            },
        ),

        migrations.RenameField(
            model_name='nakes',
            old_name='profesi',
            new_name='profesi_old',
        ),

        migrations.AddField(
            model_name='nakes',
            name='profesi_fk',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='nakes_list',
                to='nakes.profesi',
            ),
        ),

        migrations.RunPython(seed_profesi_and_migrate_data, migrations.RunPython.noop),

        migrations.RemoveField(
            model_name='nakes',
            name='profesi_old',
        ),

        migrations.RenameField(
            model_name='nakes',
            old_name='profesi_fk',
            new_name='profesi',
        ),

        migrations.AlterField(
            model_name='nakes',
            name='profesi',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='nakes_list',
                to='nakes.profesi',
            ),
        ),
    ]
