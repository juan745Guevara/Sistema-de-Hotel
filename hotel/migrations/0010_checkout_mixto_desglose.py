# Generated manually for mixto payment breakdown

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0009_reserva_creado_por'),
    ]

    operations = [
        migrations.AddField(
            model_name='checkout',
            name='mixto_efectivo',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Parte en efectivo cuando el pago es mixto',
                max_digits=10,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Mixto — efectivo',
            ),
        ),
        migrations.AddField(
            model_name='checkout',
            name='mixto_tarjeta',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Parte con tarjeta cuando el pago es mixto',
                max_digits=10,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Mixto — tarjeta',
            ),
        ),
        migrations.AddField(
            model_name='checkout',
            name='mixto_yape',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Parte por Yape cuando el pago es mixto',
                max_digits=10,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Mixto — Yape',
            ),
        ),
        migrations.AddField(
            model_name='checkout',
            name='mixto_transferencia',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Parte por transferencia cuando el pago es mixto',
                max_digits=10,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Mixto — transferencia',
            ),
        ),
    ]
