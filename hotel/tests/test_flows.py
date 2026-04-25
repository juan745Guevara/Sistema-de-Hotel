"""
Flujos principales: reserva → check-in → check-out → limpieza, walk-in, reporte registro/PDF.
"""
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from hotel.models import CheckIn, CheckOut, Habitacion, Huesped, Membership, Reserva, Tenant
from hotel.pdf_registro import build_registro_pdf
from hotel.role_permissions import role_may_access
from hotel.tenant_scope import clear_current_tenant, set_current_tenant


class TenantFlowTestCase(TestCase):
    """Contexto multi-tenant + cliente HTTP con sesión de hotel activa."""

    def setUp(self):
        clear_current_tenant()
        slug = f'test-{uuid.uuid4().hex[:10]}'
        self.tenant = Tenant.objects.create(name='Hotel pruebas', slug=slug)
        self.password = 'TestPass123!'
        self.admin = User.objects.create_user('admin_flow', password=self.password)
        Membership.objects.create(user=self.admin, tenant=self.tenant, role=Membership.ROLE_ADMIN)
        set_current_tenant(self.tenant)
        self.hab = Habitacion.objects.create(
            tenant=self.tenant,
            numero='501',
            tipo=Habitacion.TIPO_SIMPLE,
            estado=Habitacion.ESTADO_DISPONIBLE,
            capacidad=2,
            precio_noche=Decimal('80.00'),
        )
        self.hab2 = Habitacion.objects.create(
            tenant=self.tenant,
            numero='502',
            tipo=Habitacion.TIPO_SIMPLE,
            estado=Habitacion.ESTADO_DISPONIBLE,
            capacidad=2,
            precio_noche=Decimal('90.00'),
        )
        self.client = Client()

    def tearDown(self):
        clear_current_tenant()

    def _login_admin(self):
        self.client.force_login(self.admin)
        session = self.client.session
        session['active_tenant_id'] = self.tenant.pk
        session.save()


class ReservaCheckinCheckoutFlowTests(TenantFlowTestCase):
    def test_reserva_checkin_checkout_limpieza_a_disponible(self):
        """Reserva nueva → check-in → check-out deja habitación en limpieza; cola la marca disponible."""
        self._login_admin()
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        data = {
            'huesped_documento': '99988877',
            'huesped_nombre': 'Ana',
            'huesped_apellidos': 'Prueba',
            'huesped_lugar_procedencia': 'Lima',
            'habitacion': str(self.hab.pk),
            'fecha_entrada': hoy.isoformat(),
            'fecha_salida': manana.isoformat(),
            'numero_huespedes': '1',
            'notas': '',
        }
        r1 = self.client.post(reverse('crear_reserva'), data, follow=True)
        self.assertEqual(r1.status_code, 200)
        reserva = Reserva.objects.order_by('-id').first()
        self.assertIsNotNone(reserva)
        self.assertEqual(reserva.estado, Reserva.ESTADO_PENDIENTE)
        self.hab.refresh_from_db()
        self.assertEqual(self.hab.estado, Habitacion.ESTADO_RESERVADA)

        # Check-in
        ci_data = {
            'documentos_recibidos': 'on',
            'deposito': '0',
            'metodo_deposito': '',
            'mixto_efectivo': '0',
            'mixto_tarjeta': '0',
            'mixto_yape': '0',
            'mixto_transferencia': '0',
            'notas': '',
        }
        r2 = self.client.post(reverse('realizar_checkin', args=[reserva.pk]), ci_data, follow=True)
        self.assertEqual(r2.status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.ESTADO_CHECKIN)
        self.assertTrue(CheckIn.objects.filter(reserva=reserva).exists())
        self.hab.refresh_from_db()
        self.assertEqual(self.hab.estado, Habitacion.ESTADO_OCUPADA)

        # Check-out
        saldo = str(reserva.precio_total)
        co_data = {
            'total_pagado': saldo,
            'metodo_pago': CheckOut.METODO_EFECTIVO,
            'mixto_efectivo': '0',
            'mixto_tarjeta': '0',
            'mixto_yape': '0',
            'mixto_transferencia': '0',
            'danos_observados': '',
            'notas': '',
        }
        r3 = self.client.post(reverse('realizar_checkout', args=[reserva.pk]), co_data, follow=True)
        self.assertEqual(r3.status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.ESTADO_CHECKOUT)
        self.hab.refresh_from_db()
        self.assertEqual(self.hab.estado, Habitacion.ESTADO_LIMPIEZA)

        # Cola de limpieza
        r4 = self.client.get(reverse('lista_limpieza'))
        self.assertEqual(r4.status_code, 200)
        self.assertContains(r4, '501')

        r5 = self.client.post(reverse('marcar_limpieza_terminada', args=[self.hab.pk]), follow=True)
        self.assertEqual(r5.status_code, 200)
        self.hab.refresh_from_db()
        self.assertEqual(self.hab.estado, Habitacion.ESTADO_DISPONIBLE)


class WalkinFlowTests(TenantFlowTestCase):
    def test_walkin_crea_reserva_en_checkin_y_ocupa_habitacion(self):
        self._login_admin()
        data = {
            'documento_identidad': '11223344',
            'nombre': 'Luis',
            'apellidos': 'Walkin',
            'lugar_procedencia': 'Cusco',
            'habitacion': str(self.hab2.pk),
            'numero_huespedes': '1',
            'tipo_estadia': 'noches',
            'noches': '1',
            'duracion_horas': '3',
            'precio_acordado': '',
            'documentos_recibidos': 'on',
            'deposito': '0',
            'metodo_deposito': '',
            'mixto_efectivo': '0',
            'mixto_tarjeta': '0',
            'mixto_yape': '0',
            'mixto_transferencia': '0',
        }
        r = self.client.post(reverse('walkin'), data, follow=True)
        self.assertEqual(r.status_code, 200)
        reserva = Reserva.objects.filter(huesped__documento_identidad='11223344').first()
        self.assertIsNotNone(reserva)
        self.assertEqual(reserva.estado, Reserva.ESTADO_CHECKIN)
        self.hab2.refresh_from_db()
        self.assertEqual(self.hab2.estado, Habitacion.ESTADO_OCUPADA)


class ReporteRegistroTests(TenantFlowTestCase):
    def test_reporte_registro_y_pdf_admin(self):
        self._login_admin()
        h = Huesped.objects.create(
            tenant=self.tenant,
            nombre='X',
            apellidos='Y',
            documento_identidad='55667788',
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
            empleado='test',
            documentos_recibidos=True,
            deposito=Decimal('0'),
        )

        r = self.client.get(reverse('reporte_registro'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '55667788')

        rpdf = self.client.get(reverse('reporte_registro_pdf'))
        self.assertEqual(rpdf.status_code, 200)
        self.assertEqual(rpdf['Content-Type'], 'application/pdf')
        self.assertTrue(rpdf.content.startswith(b'%PDF'))

    def test_build_registro_pdf_vacio(self):
        pdf = build_registro_pdf(
            titulo_hotel='H',
            subtitulo_periodo='P',
            pie_generacion='pie',
            filas=[],
        )
        self.assertTrue(pdf.startswith(b'%PDF'))


class PermissionsFlowTests(TestCase):
    def test_recepcion_no_accede_reportes(self):
        self.assertFalse(role_may_access(Membership.ROLE_RECEPCION, 'reportes'))
        self.assertTrue(role_may_access(Membership.ROLE_ADMIN, 'reportes'))


class ReceptionReportesRedirectTests(TenantFlowTestCase):
    """Recepción no debe abrir el módulo de reportes (solo administrador del hotel)."""

    def test_recepcion_redirigida_desde_reportes(self):
        rec = User.objects.create_user('recep_flow', password=self.password)
        Membership.objects.create(user=rec, tenant=self.tenant, role=Membership.ROLE_RECEPCION)
        self.client.force_login(rec)
        s = self.client.session
        s['active_tenant_id'] = self.tenant.pk
        s.save()
        r = self.client.get(reverse('reportes'), follow=False)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse('index'))
