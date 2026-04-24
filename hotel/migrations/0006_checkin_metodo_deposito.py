from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0005_habitacion_tipos_simple_matrimonial'),
    ]

    operations = [
        migrations.AddField(
            model_name='checkin',
            name='metodo_deposito',
            field=models.CharField(
                blank=True,
                choices=[
                    ('efectivo', 'Efectivo'),
                    ('yape', 'Yape'),
                    ('transferencia', 'Transferencia'),
                ],
                help_text='Cómo se recibió el depósito (Yape, efectivo o transferencia)',
                max_length=20,
                null=True,
                verbose_name='Método del depósito',
            ),
        ),
    ]
