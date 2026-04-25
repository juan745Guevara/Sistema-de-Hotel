from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0011_checkin_deposito_mixto_desglose'),
    ]

    operations = [
        migrations.AlterField(
            model_name='huesped',
            name='nacionalidad',
            field=models.CharField(
                default='Perú',
                max_length=100,
                verbose_name='Nacionalidad',
            ),
        ),
    ]
