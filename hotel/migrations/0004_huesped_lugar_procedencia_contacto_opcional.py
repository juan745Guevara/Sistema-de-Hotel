# Generated manually for huesped: lugar_procedencia, email/teléfono opcionales

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel', '0003_membership_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='huesped',
            name='lugar_procedencia',
            field=models.CharField(
                default='',
                help_text='Ciudad o lugar de origen del huésped',
                max_length=200,
                verbose_name='Lugar de procedencia',
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='huesped',
            name='documento_identidad',
            field=models.CharField(
                help_text='Documento nacional de identidad (único por hotel)',
                max_length=50,
                verbose_name='DNI',
            ),
        ),
        migrations.AlterField(
            model_name='huesped',
            name='nombre',
            field=models.CharField(
                help_text='Nombres del huésped',
                max_length=100,
                verbose_name='Nombres',
            ),
        ),
        migrations.AlterField(
            model_name='huesped',
            name='email',
            field=models.EmailField(
                blank=True,
                default='',
                help_text='Correo electrónico de contacto (opcional)',
                max_length=254,
                verbose_name='Email',
            ),
        ),
        migrations.AlterField(
            model_name='huesped',
            name='telefono',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Número de teléfono de contacto (opcional)',
                max_length=20,
                verbose_name='Teléfono',
            ),
        ),
    ]
