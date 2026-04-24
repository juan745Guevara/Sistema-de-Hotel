from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0007_checkout_registrado_por'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserva',
            name='fecha_hora_salida_prevista',
            field=models.DateTimeField(
                blank=True,
                help_text='Para estadías por horas (p. ej. walk-in): hora en que se prevé el check-out. Si está vacío, rige solo la fecha de salida.',
                null=True,
                verbose_name='Salida prevista (fecha y hora)',
            ),
        ),
    ]
