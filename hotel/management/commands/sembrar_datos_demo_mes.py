"""
Genera datos operativos aleatorios (~1 mes) para un hotel: huéspedes, reservas,
check-in y check-out, para probar reportes de ocupación, ingresos y registro.

Uso:
  python manage.py sembrar_datos_demo_mes --slug hotel-refugio
  python manage.py sembrar_datos_demo_mes --slug hotel-refugio --dias 30 --reservas 100 --seed 42

Por defecto borra reservas, check-ins/out y huéspedes del tenant y deja habitaciones;
crea habitaciones de demo si hay pocas.
"""

import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from hotel.models import (
    CheckIn,
    CheckOut,
    Habitacion,
    Huesped,
    Membership,
    Reserva,
    Tenant,
)

NOMBRES = (
    'María', 'José', 'Rosa', 'Carlos', 'Ana', 'Luis', 'Carmen', 'Pedro', 'Lucía', 'Miguel',
    'Patricia', 'Jorge', 'Sandra', 'Diego', 'Gabriela', 'Andrés', 'Valeria', 'Ricardo', 'Daniela', 'Fernando',
)
APELLIDOS = (
    'García', 'Rodríguez', 'López', 'Martínez', 'González', 'Pérez', 'Sánchez', 'Ramírez', 'Torres', 'Flores',
    'Vargas', 'Castillo', 'Mendoza', 'Rojas', 'Silva', 'Morales', 'Reyes', 'Herrera', 'Díaz', 'Cruz',
)
CIUDADES = (
    'Lima', 'Arequipa', 'Cusco', 'Trujillo', 'Chiclayo', 'Piura', 'Iquitos', 'Huancayo', 'Tacna', 'Puno',
    'Bogotá', 'Quito', 'La Paz', 'Santiago', 'Buenos Aires',
)
TIPOS_HAB = [
    Habitacion.TIPO_SIMPLE,
    Habitacion.TIPO_MATRIMONIAL,
    Habitacion.TIPO_DOBLE,
    Habitacion.TIPO_SUITE,
]
METODOS_CO = [
    CheckOut.METODO_EFECTIVO,
    CheckOut.METODO_TARJETA,
    CheckOut.METODO_YAPE,
    CheckOut.METODO_TRANSFERENCIA,
]
METODOS_DEP = [
    CheckIn.DEPOSITO_EFECTIVO,
    CheckIn.DEPOSITO_YAPE,
    CheckIn.DEPOSITO_TRANSFERENCIA,
]


def _local_dt(d, hour, minute):
    tz = timezone.get_default_timezone()
    return timezone.make_aware(datetime.combine(d, time(hour, minute)), tz)


def _dni_unico(usados):
    while True:
        s = ''.join(str(random.randint(0, 9)) for _ in range(8))
        if s not in usados:
            usados.add(s)
            return s


def _room_free(busy_by_room, room_id, entr, sal):
    for e, s in busy_by_room[room_id]:
        if not (sal <= e or entr >= s):
            return False
    return True


def _split_mixto_checkout(total: Decimal):
    """Total en cuatro partes, al menos dos > 0, suma exacta."""
    q = Decimal('0.01')
    total = total.quantize(q)
    # cuatro partes aleatorias y normalizar
    raw = [Decimal(str(random.uniform(0.05, 0.45))) for _ in range(4)]
    s = sum(raw)
    parts = [(total * (x / s)).quantize(q) for x in raw]
    diff = total - sum(parts)
    parts[0] = (parts[0] + diff).quantize(q)
    # asegurar al menos dos > 0
    if sum(1 for p in parts if p > 0) < 2:
        parts[0] = (total / 2).quantize(q)
        parts[1] = (total - parts[0]).quantize(q)
        parts[2] = Decimal('0')
        parts[3] = Decimal('0')
    return {
        'mixto_efectivo': parts[0],
        'mixto_tarjeta': parts[1],
        'mixto_yape': parts[2],
        'mixto_transferencia': parts[3],
    }


class Command(BaseCommand):
    help = 'Genera datos demo de ~1 mes (reservas, check-in/out) para probar reportes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            required=True,
            help='Identificador (slug) del hotel, ej. hotel-refugio',
        )
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Ventana de fechas hacia atrás desde hoy (default 30).',
        )
        parser.add_argument(
            '--reservas',
            type=int,
            default=95,
            help='Cantidad objetivo de reservas a intentar crear (default 95).',
        )
        parser.add_argument(
            '--min-habitaciones',
            type=int,
            default=10,
            help='Si el hotel tiene menos habitaciones, se crean hasta este mínimo (default 10).',
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=None,
            help='Semilla para reproducir los mismos datos.',
        )
        parser.add_argument(
            '--solo-anadir',
            action='store_true',
            help='No borrar datos existentes; solo añade reservas/huéspedes (puede solapar fechas).',
        )

    def handle(self, *args, **options):
        slug = options['slug'].strip().lower()
        dias = max(7, options['dias'])
        target = max(10, options['reservas'])
        min_hab = max(4, options['min_habitaciones'])
        solo_anadir = options['solo_anadir']
        seed = options['seed']
        if seed is not None:
            random.seed(seed)

        try:
            tenant = Tenant.all_objects.get(slug=slug)
        except Tenant.DoesNotExist as e:
            raise CommandError(f'No existe un hotel con slug «{slug}».') from e

        User = get_user_model()
        staff_user = (
            Membership.objects.filter(tenant=tenant)
            .select_related('user')
            .values_list('user_id', flat=True)
            .first()
        )
        staff = User.objects.filter(pk=staff_user).first() if staff_user else None

        hoy = timezone.localdate()
        inicio = hoy - timedelta(days=dias)

        with transaction.atomic():
            if not solo_anadir:
                CheckOut.all_objects.filter(reserva__tenant=tenant).delete()
                CheckIn.all_objects.filter(reserva__tenant=tenant).delete()
                Reserva.all_objects.filter(tenant=tenant).delete()
                Huesped.all_objects.filter(tenant=tenant).delete()
                Habitacion.all_objects.filter(tenant=tenant).update(estado=Habitacion.ESTADO_DISPONIBLE)

            rooms = list(Habitacion.all_objects.filter(tenant=tenant).order_by('numero'))
            next_num = 200
            while len(rooms) < min_hab:
                num = str(next_num)
                next_num += 1
                if Habitacion.all_objects.filter(tenant=tenant, numero=num).exists():
                    continue
                hab = Habitacion.all_objects.create(
                    tenant=tenant,
                    numero=num,
                    tipo=random.choice(TIPOS_HAB),
                    estado=Habitacion.ESTADO_DISPONIBLE,
                    capacidad=random.choice([1, 2, 2, 3]),
                    precio_noche=Decimal(str(random.choice([80, 95, 110, 130, 160, 200]))),
                    descripcion='Habitación demo',
                    servicios='WiFi, TV',
                )
                rooms.append(hab)

            busy_by_room = {h.id: [] for h in rooms}
            dnis_usados = set(
                Huesped.all_objects.filter(tenant=tenant).values_list('documento_identidad', flat=True)
            )

            creadas = []
            intentos = target * 8
            while len(creadas) < target and intentos > 0:
                intentos -= 1
                entr = inicio + timedelta(days=random.randint(0, dias))
                noches = random.choices([1, 2, 3, 4], weights=[35, 35, 20, 10])[0]
                sal = entr + timedelta(days=noches)
                random.shuffle(rooms)
                hab_elegida = None
                for hab in rooms:
                    if _room_free(busy_by_room, hab.id, entr, sal):
                        hab_elegida = hab
                        break
                if not hab_elegida:
                    continue

                nombre = random.choice(NOMBRES)
                apellido = random.choice(APELLIDOS)
                doc = _dni_unico(dnis_usados)
                ciudad = random.choice(CIUDADES)

                hue = Huesped.all_objects.create(
                    tenant=tenant,
                    tipo_documento=Huesped.TIPO_DOC_DNI,
                    documento_identidad=doc,
                    nombre=nombre,
                    apellidos=apellido,
                    lugar_residencia=ciudad,
                    motivo_viaje=random.choice([c[0] for c in Huesped.MOTIVO_VIAJE_CHOICES]),
                )

                res = Reserva.all_objects.create(
                    tenant=tenant,
                    huesped=hue,
                    habitacion=hab_elegida,
                    fecha_entrada=entr,
                    fecha_salida=sal,
                    fecha_hora_salida_prevista=None,
                    numero_huespedes=random.randint(1, min(3, hab_elegida.capacidad)),
                    precio_total=Decimal('0'),
                    estado=Reserva.ESTADO_CONFIRMADA,
                    notas='',
                    creado_por=staff,
                )
                busy_by_room[hab_elegida.id].append((entr, sal))
                creadas.append(res)

            # Resolver estados según fechas respecto a hoy; check-in/out horarios coherentes.
            rnd_cancel = []
            finalizadas = []

            for res in Reserva.all_objects.filter(tenant=tenant, pk__in=[r.pk for r in creadas]):
                entr = res.fecha_entrada
                sal = res.fecha_salida
                if random.random() < 0.07 and entr >= inicio:
                    rnd_cancel.append(res)
                    continue
                hab = res.habitacion

                if sal <= hoy:
                    res.estado = Reserva.ESTADO_CHECKOUT
                    res.save(update_fields=['estado'])

                    hr_in = random.randint(14, 21)
                    min_in = random.choice([0, 15, 30, 45])
                    ci_dt = _local_dt(entr, hr_in, min_in)
                    dep_frac = random.choice([0, 0, 0.15, 0.2, 0.3, 0.4])
                    dep = (res.precio_total * Decimal(str(dep_frac))).quantize(Decimal('0.01'))
                    met_dep = None
                    if dep > 0:
                        met_dep = random.choice(METODOS_DEP)
                    CheckIn.all_objects.create(
                        reserva=res,
                        fecha_hora=ci_dt,
                        empleado='Recepción demo',
                        documentos_recibidos=random.random() < 0.85,
                        deposito=dep,
                        metodo_deposito=met_dep,
                        notas='',
                    )

                    hr_out = random.randint(8, 12)
                    co_day = sal
                    co_dt = _local_dt(co_day, hr_out, random.choice([0, 10, 20, 30]))

                    metodo = random.choices(
                        METODOS_CO + [CheckOut.METODO_MIXTO],
                        weights=[22, 22, 22, 22, 12],
                        k=1,
                    )[0]
                    extra = {}
                    if metodo == CheckOut.METODO_MIXTO:
                        extra = _split_mixto_checkout(res.precio_total)

                    CheckOut.all_objects.create(
                        reserva=res,
                        fecha_hora=co_dt,
                        registrado_por=staff,
                        total_pagado=res.precio_total,
                        metodo_pago=metodo,
                        calificacion=random.choice([3, 4, 4, 5, 5, None]),
                        notas='',
                        **extra,
                    )
                    finalizadas.append(res)

                elif entr <= hoy < sal:
                    res.estado = Reserva.ESTADO_CHECKIN
                    res.save(update_fields=['estado'])
                    ci_dt = _local_dt(entr, random.randint(15, 20), random.choice([0, 15, 30]))
                    CheckIn.all_objects.create(
                        reserva=res,
                        fecha_hora=ci_dt,
                        empleado='Recepción demo',
                        documentos_recibidos=True,
                        deposito=Decimal('0'),
                        metodo_deposito=None,
                        notas='En casa (demo)',
                    )
                else:
                    if random.random() < 0.5:
                        res.estado = Reserva.ESTADO_PENDIENTE
                    else:
                        res.estado = Reserva.ESTADO_CONFIRMADA
                    res.save(update_fields=['estado'])

            for res in rnd_cancel:
                res.estado = Reserva.ESTADO_CANCELADA
                res.save(update_fields=['estado'])

            Habitacion.all_objects.filter(tenant=tenant).update(estado=Habitacion.ESTADO_DISPONIBLE)

        self.stdout.write(
            self.style.SUCCESS(
                f'Hotel «{tenant.name}» ({tenant.slug}): '
                f'{len(creadas)} reserva(s) generadas; '
                f'{len(rnd_cancel)} cancelada(s); '
                f'{len(finalizadas)} con check-out en el período; '
                f'{Habitacion.all_objects.filter(tenant=tenant).count()} habitación(es). '
                f'Rango aproximado: {inicio} → {hoy}.'
            )
        )
