"""
Tests adicionales: cancelar, edición bloqueada, búsqueda, habitaciones, depósitos, mixto, roles, utilidades.
"""
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from hotel.models import CheckIn, CheckOut, Habitacion, Huesped, Membership, Reserva, Tenant
from hotel.views import _resolver_rango_fechas

from .test_flows import TenantFlowTestCase


class CancelarReservaTests(TenantFlowTestCase):
    def test_cancelar_reserva_pendiente_libera_habitacion(self):
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        self.client.post(
            reverse('crear_reserva'),
            {
                'huesped_tipo_documento': 'dni',
                'huesped_documento': '44411122',
                'huesped_nombre': 'Carla',
                'huesped_apellidos': 'Cancel',
                'huesped_lugar_procedencia': 'Lima',
                'habitacion': str(self.hab.pk),
                'fecha_entrada': hoy.isoformat(),
                'fecha_salida': manana.isoformat(),
                'numero_huespedes': '1',
                'notas': '',
            },
            follow=True,
        )
        reserva = Reserva.objects.get(huesped__documento_identidad='44411122')
        self.assertEqual(reserva.estado, Reserva.ESTADO_PENDIENTE)
        self.hab.refresh_from_db()
        self.assertEqual(self.hab.estado, Habitacion.ESTADO_RESERVADA)

        r = self.client.post(reverse('cancelar_reserva', args=[reserva.pk]), follow=True)
        self.assertEqual(r.status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.ESTADO_CANCELADA)
        self.hab.refresh_from_db()
        self.assertEqual(self.hab.estado, Habitacion.ESTADO_DISPONIBLE)

    def test_no_cancelar_si_ya_hay_checkin(self):
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        self.client.post(
            reverse('crear_reserva'),
            {
                'huesped_tipo_documento': 'dni',
                'huesped_documento': '33322211',
                'huesped_nombre': 'Ben',
                'huesped_apellidos': 'Check',
                'huesped_lugar_procedencia': 'Arequipa',
                'habitacion': str(self.hab.pk),
                'fecha_entrada': hoy.isoformat(),
                'fecha_salida': manana.isoformat(),
                'numero_huespedes': '1',
                'notas': '',
            },
        )
        reserva = Reserva.objects.get(huesped__documento_identidad='33322211')
        self.client.post(
            reverse('realizar_checkin', args=[reserva.pk]),
            {
                'documentos_recibidos': 'on',
                'deposito': '0',
                'metodo_deposito': '',
                'mixto_efectivo': '0',
                'mixto_tarjeta': '0',
                'mixto_yape': '0',
                'mixto_transferencia': '0',
                'notas': '',
            },
        )
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.ESTADO_CHECKIN)

        self.client.post(reverse('cancelar_reserva', args=[reserva.pk]), follow=True)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.ESTADO_CHECKIN)


class EditarReservaBloqueadaTests(TenantFlowTestCase):
    def test_editar_redirige_si_reserva_en_checkin(self):
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        self.client.post(
            reverse('crear_reserva'),
            {
                'huesped_tipo_documento': 'dni',
                'huesped_documento': '77788899',
                'huesped_nombre': 'Dana',
                'huesped_apellidos': 'Edit',
                'huesped_lugar_procedencia': 'Trujillo',
                'habitacion': str(self.hab.pk),
                'fecha_entrada': hoy.isoformat(),
                'fecha_salida': manana.isoformat(),
                'numero_huespedes': '1',
                'notas': '',
            },
        )
        reserva = Reserva.objects.get(huesped__documento_identidad='77788899')
        self.client.post(
            reverse('realizar_checkin', args=[reserva.pk]),
            {
                'documentos_recibidos': 'on',
                'deposito': '0',
                'metodo_deposito': '',
                'mixto_efectivo': '0',
                'mixto_tarjeta': '0',
                'mixto_yape': '0',
                'mixto_transferencia': '0',
                'notas': '',
            },
        )
        r = self.client.get(reverse('editar_reserva', args=[reserva.pk]), follow=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse('detalle_reserva', args=[reserva.pk]))


class BusquedaRapidaTests(TenantFlowTestCase):
    def test_busqueda_devuelve_reserva_por_documento(self):
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        self.client.post(
            reverse('crear_reserva'),
            {
                'huesped_tipo_documento': 'dni',
                'huesped_documento': '12121212',
                'huesped_nombre': 'Eva',
                'huesped_apellidos': 'Busq',
                'huesped_lugar_procedencia': 'Lima',
                'habitacion': str(self.hab2.pk),
                'fecha_entrada': hoy.isoformat(),
                'fecha_salida': manana.isoformat(),
                'numero_huespedes': '1',
                'notas': '',
            },
        )
        reserva = Reserva.objects.get(huesped__documento_identidad='12121212')
        r = self.client.get(reverse('busqueda_rapida'), {'q': '12121212'})
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content.decode())
        self.assertTrue(any(x['id'] == reserva.id for x in data['reservas']))


class EliminarHabitacionTests(TenantFlowTestCase):
    def test_eliminar_habitacion_sin_reservas(self):
        self._login_admin()
        h3 = Habitacion.objects.create(
            tenant=self.tenant,
            numero='Z900',
            tipo=Habitacion.TIPO_SIMPLE,
            estado=Habitacion.ESTADO_DISPONIBLE,
            capacidad=1,
            precio_noche=Decimal('40.00'),
        )
        r = self.client.post(reverse('eliminar_habitacion', args=[h3.pk]), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Habitacion.objects.filter(pk=h3.pk).exists())

    def test_no_eliminar_habitacion_con_reservas(self):
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        self.client.post(
            reverse('crear_reserva'),
            {
                'huesped_tipo_documento': 'dni',
                'huesped_documento': '65656565',
                'huesped_nombre': 'Fio',
                'huesped_apellidos': 'Res',
                'huesped_lugar_procedencia': 'Lima',
                'habitacion': str(self.hab.pk),
                'fecha_entrada': hoy.isoformat(),
                'fecha_salida': manana.isoformat(),
                'numero_huespedes': '1',
                'notas': '',
            },
        )
        r = self.client.post(reverse('eliminar_habitacion', args=[self.hab.pk]), follow=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse('detalle_habitacion', args=[self.hab.pk]))
        self.assertTrue(Habitacion.objects.filter(pk=self.hab.pk).exists())


class CheckinDepositoTests(TenantFlowTestCase):
    def test_checkin_con_deposito_efectivo(self):
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        self.client.post(
            reverse('crear_reserva'),
            {
                'huesped_tipo_documento': 'dni',
                'huesped_documento': '41414141',
                'huesped_nombre': 'Gus',
                'huesped_apellidos': 'Dep',
                'huesped_lugar_procedencia': 'Lima',
                'habitacion': str(self.hab.pk),
                'fecha_entrada': hoy.isoformat(),
                'fecha_salida': manana.isoformat(),
                'numero_huespedes': '1',
                'notas': '',
            },
        )
        reserva = Reserva.objects.get(huesped__documento_identidad='41414141')
        self.client.post(
            reverse('realizar_checkin', args=[reserva.pk]),
            {
                'documentos_recibidos': 'on',
                'deposito': '25.50',
                'metodo_deposito': CheckIn.DEPOSITO_EFECTIVO,
                'mixto_efectivo': '0',
                'mixto_tarjeta': '0',
                'mixto_yape': '0',
                'mixto_transferencia': '0',
                'notas': '',
            },
            follow=True,
        )
        ci = CheckIn.objects.get(reserva=reserva)
        self.assertEqual(ci.deposito, Decimal('25.50'))
        self.assertEqual(ci.metodo_deposito, CheckIn.DEPOSITO_EFECTIVO)


class CheckoutMixtoFlowTests(TenantFlowTestCase):
    def test_checkout_mixto_efectivo_y_yape(self):
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        self.client.post(
            reverse('crear_reserva'),
            {
                'huesped_tipo_documento': 'dni',
                'huesped_documento': '30303030',
                'huesped_nombre': 'Helo',
                'huesped_apellidos': 'Mix',
                'huesped_lugar_procedencia': 'Lima',
                'habitacion': str(self.hab.pk),
                'fecha_entrada': hoy.isoformat(),
                'fecha_salida': manana.isoformat(),
                'numero_huespedes': '1',
                'notas': '',
            },
        )
        reserva = Reserva.objects.get(huesped__documento_identidad='30303030')
        self.client.post(
            reverse('realizar_checkin', args=[reserva.pk]),
            {
                'documentos_recibidos': 'on',
                'deposito': '0',
                'metodo_deposito': '',
                'mixto_efectivo': '0',
                'mixto_tarjeta': '0',
                'mixto_yape': '0',
                'mixto_transferencia': '0',
                'notas': '',
            },
        )
        total = str(reserva.precio_total)
        tdec = Decimal(total)
        mitad = (tdec / 2).quantize(Decimal('0.01'))
        resto = (tdec - mitad).quantize(Decimal('0.01'))
        self.client.post(
            reverse('realizar_checkout', args=[reserva.pk]),
            {
                'total_pagado': total,
                'metodo_pago': CheckOut.METODO_MIXTO,
                'mixto_efectivo': str(mitad),
                'mixto_tarjeta': '0',
                'mixto_yape': str(resto),
                'mixto_transferencia': '0',
                'danos_observados': '',
                'notas': '',
            },
            follow=True,
        )
        co = CheckOut.objects.get(reserva=reserva)
        self.assertEqual(co.metodo_pago, CheckOut.METODO_MIXTO)
        self.assertEqual(co.mixto_efectivo, mitad)
        self.assertEqual(co.mixto_yape, resto)


class DocumentoExtranjeroTests(TenantFlowTestCase):
    def test_reserva_con_carnet_extranjeria(self):
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        self.client.post(
            reverse('crear_reserva'),
            {
                'huesped_tipo_documento': 'carnet_extranjeria',
                'huesped_documento': '001-ab12345',
                'huesped_nombre': 'Jane',
                'huesped_apellidos': 'Extranj',
                'huesped_lugar_procedencia': 'Buenos Aires',
                'huesped_nacionalidad': 'Colombiano',
                'habitacion': str(self.hab2.pk),
                'fecha_entrada': hoy.isoformat(),
                'fecha_salida': manana.isoformat(),
                'numero_huespedes': '1',
                'notas': '',
            },
            follow=True,
        )
        h = Huesped.objects.get(
            tipo_documento=Huesped.TIPO_DOC_CARNET_EXTRANJERIA,
            documento_identidad='001-AB12345',
        )
        self.assertEqual(h.nombre, 'Jane')


class ReporteOcupacionAccessTests(TenantFlowTestCase):
    def test_reporte_ocupacion_ok_admin(self):
        self._login_admin()
        r = self.client.get(reverse('reporte_ocupacion'))
        self.assertEqual(r.status_code, 200)


class RolLimpiezaCrearReservaTests(TenantFlowTestCase):
    def test_limpieza_no_accede_crear_reserva(self):
        lim = User.objects.create_user('lim_flow_x', password=self.password)
        Membership.objects.create(user=lim, tenant=self.tenant, role=Membership.ROLE_LIMPIEZA)
        self.client.force_login(lim)
        s = self.client.session
        s['active_tenant_id'] = self.tenant.pk
        s.save()
        r = self.client.get(reverse('crear_reserva'), follow=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse('index'))


class CrearReservaCapacidadInvalidaTests(TenantFlowTestCase):
    def test_rechaza_mas_huespedes_que_capacidad(self):
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        r = self.client.post(
            reverse('crear_reserva'),
            {
                'huesped_tipo_documento': 'dni',
                'huesped_documento': '18181818',
                'huesped_nombre': 'Ivo',
                'huesped_apellidos': 'Cap',
                'huesped_lugar_procedencia': 'Lima',
                'habitacion': str(self.hab.pk),
                'fecha_entrada': hoy.isoformat(),
                'fecha_salida': manana.isoformat(),
                'numero_huespedes': '99',
                'notas': '',
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'La habitación permite hasta', status_code=200)


class ResolverRangoFechasTests(TestCase):
    def test_intercambia_si_desde_mayor_que_hasta(self):
        rf = RequestFactory()
        req = rf.get(
            '/x/',
            {'fecha_desde': '2030-12-31', 'fecha_hasta': '2030-01-01'},
        )
        d0, d1 = _resolver_rango_fechas(req)
        self.assertLessEqual(d0, d1)
        self.assertEqual(d0.year, 2030)
        self.assertEqual(d1.month, 12)


class TableroYDisponibilidadTests(TenantFlowTestCase):
    def test_tablero_y_disponibilidad_responden(self):
        self._login_admin()
        self.assertEqual(self.client.get(reverse('tablero_habitaciones')).status_code, 200)
        self.assertEqual(self.client.get(reverse('disponibilidad_habitaciones')).status_code, 200)


class RecepcionCambioEstadoHabitacionTests(TenantFlowTestCase):
    def test_recepcion_puede_cambiar_estado_como_admin(self):
        rec = User.objects.create_user('rec_estado', password=self.password)
        Membership.objects.create(user=rec, tenant=self.tenant, role=Membership.ROLE_RECEPCION)
        self.client.force_login(rec)
        s = self.client.session
        s['active_tenant_id'] = self.tenant.pk
        s.save()
        self.assertEqual(self.hab.estado, Habitacion.ESTADO_DISPONIBLE)
        r = self.client.post(
            reverse('actualizar_estado_habitacion', args=[self.hab.pk]),
            {'estado': Habitacion.ESTADO_MANTENIMIENTO},
            follow=False,
        )
        self.assertEqual(r.status_code, 302)
        self.hab.refresh_from_db()
        self.assertEqual(self.hab.estado, Habitacion.ESTADO_MANTENIMIENTO)


class ListaCheckinsFiltroDiaTests(TenantFlowTestCase):
    def test_lista_checkins_con_fecha(self):
        self._login_admin()
        h = Huesped.objects.create(
            tenant=self.tenant,
            nombre='J',
            apellidos='K',
            documento_identidad='91919191',
            lugar_procedencia='Lima',
            email='',
            telefono='',
        )
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        reserva = Reserva.objects.create(
            tenant=self.tenant,
            huesped=h,
            habitacion=self.hab,
            fecha_entrada=hoy,
            fecha_salida=manana,
            numero_huespedes=1,
            precio_total=Decimal('80.00'),
            estado=Reserva.ESTADO_CHECKIN,
        )
        CheckIn.objects.create(
            reserva=reserva,
            fecha_hora=timezone.now(),
            empleado='t',
            documentos_recibidos=False,
            deposito=Decimal('0'),
        )
        r = self.client.get(
            reverse('lista_checkins'),
            {'fecha_desde': hoy.isoformat(), 'fecha_hasta': hoy.isoformat()},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'J K')  # nombre_completo en la tabla
