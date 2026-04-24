"""
Limpieza de datos de prueba.

Modo normal: reservas, check-in/out, huéspedes; habitaciones a disponible.

Modo --completo: además borra todos los tenants (hotels, habitaciones, membresías)
y todas las cuentas de usuario. Base lista para createsuperuser y alta desde cero.
"""

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction

from hotel.models import CheckIn, CheckOut, Habitacion, Huesped, Reserva, Tenant


class Command(BaseCommand):
    help = (
        'Borra datos operativos. Con --completo también tenants y todas las cuentas de usuario.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Confirmar sin preguntar (útil en scripts).',
        )
        parser.add_argument(
            '--completo',
            action='store_true',
            help='Borrar también hotels (tenants), catálogo de habitaciones y todos los usuarios.',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            self.stderr.write(
                'Ejecuta con --yes (y opcionalmente --completo). Ejemplos:\n'
                '  python manage.py limpiar_datos_operativos --yes\n'
                '  python manage.py limpiar_datos_operativos --yes --completo\n'
            )
            return

        User = get_user_model()

        with transaction.atomic():
            n_sess = Session.objects.count()
            Session.objects.all().delete()

            if options['completo']:
                n_ten = Tenant.all_objects.count()
                n_u = User.objects.count()
                # Cascada: membresías, habitaciones, huéspedes, reservas, check-in/out
                Tenant.all_objects.all().delete()
                User.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Reset completo: {n_ten} hotel(es) y datos asociados eliminados; '
                        f'{n_u} cuenta(s) de usuario borrada(s); {n_sess} sesión(es) cerradas.\n'
                        'Siguiente paso: registro en /accounts/signup/ (crea usuario + hotel) '
                        'o `python manage.py createsuperuser` y luego alta de hotel en el admin.'
                    )
                )
                return

            n_res = Reserva.all_objects.count()
            n_hue = Huesped.all_objects.count()
            Reserva.all_objects.all().delete()
            Huesped.all_objects.all().delete()
            CheckIn.all_objects.all().delete()
            CheckOut.all_objects.all().delete()
            updated = Habitacion.all_objects.update(estado=Habitacion.ESTADO_DISPONIBLE)

        self.stdout.write(
            self.style.SUCCESS(
                f'Listo: {n_res} reserva(s), {n_hue} huésped(es) eliminados; '
                f'{updated} habitación(es) en estado disponible; '
                f'{n_sess} sesión(es) cerradas. (Usuarios y hotels sin cambios.)'
            )
        )
