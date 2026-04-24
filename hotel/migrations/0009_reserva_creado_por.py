from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('hotel', '0008_reserva_fecha_hora_salida_prevista'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserva',
            name='creado_por',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuario (p. ej. administrador o recepción) que registró la reserva en el sistema.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reservas_creadas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Creada por',
            ),
        ),
    ]
