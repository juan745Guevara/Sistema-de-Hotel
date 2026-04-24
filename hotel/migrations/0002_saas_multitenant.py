# SaaS multi-tenant: Tenant, Membership, FK tenant en datos existentes.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_default_tenant_and_assign(apps, schema_editor):
    Tenant = apps.get_model('hotel', 'Tenant')
    Habitacion = apps.get_model('hotel', 'Habitacion')
    Huesped = apps.get_model('hotel', 'Huesped')
    Reserva = apps.get_model('hotel', 'Reserva')
    User = apps.get_model('auth', 'User')
    Membership = apps.get_model('hotel', 'Membership')

    tenant = Tenant.objects.create(name='Hotel por defecto', slug='legacy-default-hotel')
    Habitacion.objects.update(tenant=tenant)
    Huesped.objects.update(tenant=tenant)
    Reserva.objects.update(tenant=tenant)
    for user in User.objects.all():
        Membership.objects.get_or_create(
            user=user,
            tenant=tenant,
            defaults={'role': 'owner'},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nombre del hotel')),
                ('slug', models.SlugField(max_length=80, unique=True, verbose_name='Identificador URL')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creado')),
            ],
            options={
                'verbose_name': 'Hotel (tenant)',
                'verbose_name_plural': 'Hoteles (tenants)',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'role',
                    models.CharField(
                        choices=[('owner', 'Propietario'), ('staff', 'Personal')],
                        default='staff',
                        max_length=20,
                    ),
                ),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                (
                    'tenant',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='memberships',
                        to='hotel.tenant',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tenant_memberships',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Membresía',
                'verbose_name_plural': 'Membresías',
            },
        ),
        migrations.AddField(
            model_name='habitacion',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='habitaciones',
                to='hotel.tenant',
                verbose_name='Hotel',
            ),
        ),
        migrations.AddField(
            model_name='huesped',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='huespedes',
                to='hotel.tenant',
                verbose_name='Hotel',
            ),
        ),
        migrations.AddField(
            model_name='reserva',
            name='tenant',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='reservas',
                to='hotel.tenant',
                verbose_name='Hotel',
            ),
        ),
        migrations.RunPython(create_default_tenant_and_assign, noop_reverse),
        migrations.AlterField(
            model_name='habitacion',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='habitaciones',
                to='hotel.tenant',
                verbose_name='Hotel',
            ),
        ),
        migrations.AlterField(
            model_name='huesped',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='huespedes',
                to='hotel.tenant',
                verbose_name='Hotel',
            ),
        ),
        migrations.AlterField(
            model_name='reserva',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='reservas',
                to='hotel.tenant',
                verbose_name='Hotel',
            ),
        ),
        migrations.AlterField(
            model_name='habitacion',
            name='numero',
            field=models.CharField(
                help_text='Número de habitación único dentro de este hotel',
                max_length=10,
                verbose_name='Número de Habitación',
            ),
        ),
        migrations.AlterField(
            model_name='huesped',
            name='documento_identidad',
            field=models.CharField(
                help_text='Pasaporte, DNI, CURP u otro documento oficial (único por hotel)',
                max_length=50,
                verbose_name='Documento de Identidad',
            ),
        ),
        migrations.AddConstraint(
            model_name='membership',
            constraint=models.UniqueConstraint(
                fields=('user', 'tenant'),
                name='unique_membership_user_tenant',
            ),
        ),
        migrations.AddConstraint(
            model_name='habitacion',
            constraint=models.UniqueConstraint(
                fields=('tenant', 'numero'),
                name='uniq_habitacion_tenant_numero',
            ),
        ),
        migrations.AddConstraint(
            model_name='huesped',
            constraint=models.UniqueConstraint(
                fields=('tenant', 'documento_identidad'),
                name='uniq_huesped_tenant_documento',
            ),
        ),
        migrations.AddIndex(
            model_name='habitacion',
            index=models.Index(fields=['estado'], name='hotel_habitacion_estado_idx'),
        ),
        migrations.AddIndex(
            model_name='habitacion',
            index=models.Index(fields=['tipo'], name='hotel_habitacion_tipo_idx'),
        ),
        migrations.AddIndex(
            model_name='huesped',
            index=models.Index(
                fields=['apellidos', 'nombre'],
                name='hotel_huesped_apell_nom_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='reserva',
            index=models.Index(
                fields=['fecha_entrada', 'fecha_salida'],
                name='hotel_reserva_fechas_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='reserva',
            index=models.Index(fields=['estado'], name='hotel_reserva_estado_idx'),
        ),
        migrations.AddIndex(
            model_name='reserva',
            index=models.Index(fields=['huesped'], name='hotel_reserva_huesped_idx'),
        ),
        migrations.AddIndex(
            model_name='reserva',
            index=models.Index(fields=['habitacion'], name='hotel_reserva_habitacion_idx'),
        ),
        migrations.AddIndex(
            model_name='reserva',
            index=models.Index(
                fields=['tenant', 'estado'],
                name='hotel_reserva_tenant_estado_idx',
            ),
        ),
    ]
