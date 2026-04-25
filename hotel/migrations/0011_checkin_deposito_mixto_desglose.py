# Depósito mixto con desglose (alineado con check-out)

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0010_checkout_mixto_desglose'),
    ]

    operations = [
        migrations.AlterField(
            model_name='checkin',
            name='metodo_deposito',
            field=models.CharField(
                blank=True,
                choices=[
                    ('efectivo', 'Efectivo'),
                    ('yape', 'Yape'),
                    ('transferencia', 'Transferencia'),
                    ('mixto', 'Mixto'),
                ],
                help_text='Cómo se recibió el depósito (incluye mixto con desglose)',
                max_length=20,
                null=True,
                verbose_name='Método del depósito',
            ),
        ),
        migrations.AddField(
            model_name='checkin',
            name='mixto_efectivo',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Parte en efectivo cuando el depósito es mixto',
                max_digits=10,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Dep. mixto — efectivo',
            ),
        ),
        migrations.AddField(
            model_name='checkin',
            name='mixto_tarjeta',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Parte con tarjeta cuando el depósito es mixto',
                max_digits=10,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Dep. mixto — tarjeta',
            ),
        ),
        migrations.AddField(
            model_name='checkin',
            name='mixto_yape',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Parte por Yape cuando el depósito es mixto',
                max_digits=10,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Dep. mixto — Yape',
            ),
        ),
        migrations.AddField(
            model_name='checkin',
            name='mixto_transferencia',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Parte por transferencia cuando el depósito es mixto',
                max_digits=10,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Dep. mixto — transferencia',
            ),
        ),
    ]
