from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('hotel', '0006_checkin_metodo_deposito'),
    ]

    operations = [
        migrations.AddField(
            model_name='checkout',
            name='registrado_por',
            field=models.ForeignKey(
                blank=True,
                help_text='Usuario de la cuenta que registró el check-out',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='checkouts_registrados',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Registrado por',
            ),
        ),
        migrations.RemoveField(
            model_name='checkout',
            name='empleado',
        ),
    ]
