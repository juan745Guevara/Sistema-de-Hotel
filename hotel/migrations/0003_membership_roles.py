# Roles: admin / recepcion / limpieza (antes owner / staff)

from django.db import migrations, models


def forwards_migrate_roles(apps, schema_editor):
    Membership = apps.get_model('hotel', 'Membership')
    Membership.objects.filter(role='owner').update(role='admin')
    Membership.objects.filter(role='staff').update(role='recepcion')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0002_saas_multitenant'),
    ]

    operations = [
        migrations.RunPython(forwards_migrate_roles, noop_reverse),
        migrations.AlterField(
            model_name='membership',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Administrador'),
                    ('recepcion', 'Recepción'),
                    ('limpieza', 'Personal de limpieza'),
                ],
                default='recepcion',
                max_length=20,
            ),
        ),
    ]
