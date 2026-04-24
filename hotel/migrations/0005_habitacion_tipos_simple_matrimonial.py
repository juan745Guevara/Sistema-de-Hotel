# Tipos: simple, matrimonial, doble, suite, presidencial (antes: sencilla → simple).

from django.db import migrations, models


def forwards(apps, schema_editor):
    Habitacion = apps.get_model('hotel', 'Habitacion')
    Habitacion._base_manager.filter(tipo='sencilla').update(tipo='simple')


def backwards(apps, schema_editor):
    Habitacion = apps.get_model('hotel', 'Habitacion')
    Habitacion._base_manager.filter(tipo='simple').update(tipo='sencilla')


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0004_huesped_lugar_procedencia_contacto_opcional'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name='habitacion',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('simple', 'Simple'),
                    ('matrimonial', 'Matrimonial'),
                    ('doble', 'Doble'),
                    ('suite', 'Suite'),
                    ('presidencial', 'Presidencial'),
                ],
                help_text='Tipo de habitación',
                max_length=20,
                verbose_name='Tipo',
            ),
        ),
    ]
