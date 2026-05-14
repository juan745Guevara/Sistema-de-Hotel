"""
Modelos del Sistema Hotelero

Este módulo contiene todos los modelos de datos del sistema:
- Habitacion: Representa las habitaciones del hotel
- Huesped: Representa a los huéspedes/clientes
- Reserva: Representa las reservas realizadas
- CheckIn: Registro de check-in de una reserva
- CheckOut: Registro de check-out de una reserva
"""

from datetime import datetime, time
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .tenant_scope import get_current_tenant
from .tenant_managers import AllObjectsManager, TenantScopedManager, ThroughReservaTenantManager


class Tenant(models.Model):
    """Hotel u organización suscriptora (multi-tenant SaaS)."""

    name = models.CharField(max_length=200, verbose_name='Nombre del hotel')
    slug = models.SlugField(max_length=80, unique=True, verbose_name='Identificador URL')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')

    objects = models.Manager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = 'Hotel (tenant)'
        verbose_name_plural = 'Hoteles (tenants)'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:72] or 'hotel'
            self.slug = base
            n = 0
            while Tenant.all_objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                n += 1
                self.slug = f'{base}-{n}'
        super().save(*args, **kwargs)


class Membership(models.Model):
    """Usuario perteneciente a un hotel."""

    ROLE_ADMIN = 'admin'
    ROLE_RECEPCION = 'recepcion'
    ROLE_LIMPIEZA = 'limpieza'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Administrador'),
        (ROLE_RECEPCION, 'Recepción'),
        (ROLE_LIMPIEZA, 'Personal de limpieza'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_memberships',
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_RECEPCION)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Membresía'
        verbose_name_plural = 'Membresías'
        constraints = [
            models.UniqueConstraint(fields=['user', 'tenant'], name='unique_membership_user_tenant'),
        ]
        indexes = [
            models.Index(fields=['tenant', 'user'], name='hotel_member_tenant_user_idx'),
        ]

    def __str__(self):
        return f'{self.user} @ {self.tenant}'


class Habitacion(models.Model):
    """
    Modelo que representa una habitación del hotel.
    
    Cada habitación tiene un número único, tipo, estado actual,
    capacidad, precio y servicios incluidos.
    """
    
    # ========== CONSTANTES Y CHOICES ==========
    
    ESTADO_DISPONIBLE = 'disponible'
    ESTADO_OCUPADA = 'ocupada'
    ESTADO_MANTENIMIENTO = 'mantenimiento'
    ESTADO_LIMPIEZA = 'limpieza'
    ESTADO_RESERVADA = 'reservada'
    
    ESTADO_CHOICES = [
        (ESTADO_DISPONIBLE, 'Disponible'),
        (ESTADO_OCUPADA, 'Ocupada'),
        (ESTADO_MANTENIMIENTO, 'En Mantenimiento'),
        (ESTADO_LIMPIEZA, 'En Limpieza'),
        (ESTADO_RESERVADA, 'Reservada'),
    ]
    
    TIPO_SIMPLE = 'simple'
    TIPO_MATRIMONIAL = 'matrimonial'
    TIPO_DOBLE = 'doble'
    TIPO_SUITE = 'suite'
    TIPO_PRESIDENCIAL = 'presidencial'

    TIPO_CHOICES = [
        (TIPO_SIMPLE, 'Simple'),
        (TIPO_MATRIMONIAL, 'Matrimonial'),
        (TIPO_DOBLE, 'Doble'),
        (TIPO_SUITE, 'Suite'),
        (TIPO_PRESIDENCIAL, 'Presidencial'),
    ]
    
    # ========== MULTI-TENANT ==========
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='habitaciones',
        verbose_name='Hotel',
    )

    # ========== CAMPOS BÁSICOS (Identificación) ==========

    numero = models.CharField(
        max_length=10,
        verbose_name='Número de Habitación',
        help_text='Número de habitación único dentro de este hotel'
    )
    
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name='Tipo',
        help_text='Tipo de habitación'
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_DISPONIBLE,
        verbose_name='Estado',
        help_text='Estado actual de la habitación'
    )
    
    # ========== CAMPOS DE CONFIGURACIÓN ==========
    
    capacidad = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Capacidad',
        help_text='Número máximo de personas que puede alojar'
    )
    
    precio_noche = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Precio por noche (soles)',
        help_text='Precio base por noche en soles (PEN)'
    )
    
    # ========== CAMPOS OPCIONALES (Información adicional) ==========
    
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
        help_text='Descripción detallada de la habitación'
    )
    
    servicios = models.TextField(
        blank=True,
        verbose_name='Servicios',
        help_text='Servicios incluidos (WiFi, TV, minibar, etc.)'
    )
    
    # ========== CAMPOS DE AUDITORÍA ==========
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Actualización'
    )

    objects = TenantScopedManager()
    all_objects = AllObjectsManager()

    # ========== META Y MÉTODOS ==========

    class Meta:
        verbose_name = 'Habitación'
        verbose_name_plural = 'Habitaciones'
        ordering = ['numero']
        base_manager_name = 'all_objects'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'numero'],
                name='uniq_habitacion_tenant_numero',
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'numero']),
            models.Index(fields=['estado']),
            models.Index(fields=['tipo']),
        ]

    def save(self, *args, **kwargs):
        t = get_current_tenant()
        if t is not None and self.tenant_id is None:
            self.tenant = t
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Habitación {self.numero} - {self.get_tipo_display()}'


class Huesped(models.Model):
    """
    Modelo que representa a un huésped (cliente) del hotel.

    Almacena información personal del huésped para el registro y el servicio.
    """

    TIPO_DOC_DNI = 'dni'
    TIPO_DOC_CARNET_EXTRANJERIA = 'carnet_extranjeria'
    TIPO_DOC_PASAPORTE = 'pasaporte'
    TIPO_DOC_OTRO = 'otro'

    TIPO_DOCUMENTO_CHOICES = [
        (TIPO_DOC_DNI, 'DNI (Perú)'),
        (TIPO_DOC_CARNET_EXTRANJERIA, 'Carné de extranjería (CE)'),
        (TIPO_DOC_PASAPORTE, 'Pasaporte'),
        (TIPO_DOC_OTRO, 'Otro documento'),
    ]

    # Lista (controlada) de nacionalidades para el formulario.
    # Para DNI se fuerza 'Perú' automáticamente en el backend.
    NACIONALIDAD_PERU = 'Perú'
    _NACIONALIDADES_RAW = [
        (NACIONALIDAD_PERU, 'Perú'),
        ('Mexicano', 'Mexicano'),
        ('Colombiano', 'Colombiano'),
        ('Ecuatoriano', 'Ecuatoriano'),
        ('Venezolano', 'Venezolano'),
        ('Argentino', 'Argentino'),
        ('Chileno', 'Chileno'),
        ('Boliviano', 'Boliviano'),
        ('Uruguayo', 'Uruguayo'),
        ('Paraguayo', 'Paraguayo'),
        ('Brasileño', 'Brasileño'),
        ('Costarricense', 'Costarricense'),
        ('Guatemalteco', 'Guatemalteco'),
        ('Hondureño', 'Hondureño'),
        ('Salvadoreño', 'Salvadoreño'),
        ('Nicaragüense', 'Nicaragüense'),
        ('Panameño', 'Panameño'),
        ('Dominicano', 'Dominicano'),
        ('Cubano', 'Cubano'),
        ('Haitiano', 'Haitiano'),
        ('Jamaicano', 'Jamaicano'),
        ('Trinitense', 'Trinitense'),
        ('Estadounidense', 'Estadounidense'),
        ('Canadiense', 'Canadiense'),
        ('Español', 'Español'),
        ('Portugués', 'Portugués'),
        ('Francés', 'Francés'),
        ('Alemán', 'Alemán'),
        ('Italiano', 'Italiano'),
        ('Británico', 'Británico'),
        ('Irlandés', 'Irlandés'),
        ('Belga', 'Belga'),
        ('Neerlandés', 'Neerlandés'),
        ('Suizo', 'Suizo'),
        ('Austríaco', 'Austríaco'),
        ('Sueco', 'Sueco'),
        ('Noruego', 'Noruego'),
        ('Danés', 'Danés'),
        ('Finlandés', 'Finlandés'),
        ('Polaco', 'Polaco'),
        ('Rumano', 'Rumano'),
        ('Ucraniano', 'Ucraniano'),
        ('Ruso', 'Ruso'),
        ('Turco', 'Turco'),
        ('Griego', 'Griego'),
        ('Marroquí', 'Marroquí'),
        ('Argelino', 'Argelino'),
        ('Tunecino', 'Tunecino'),
        ('Egipcio', 'Egipcio'),
        ('Sudafricano', 'Sudafricano'),
        ('Nigeriano', 'Nigeriano'),
        ('Ghanés', 'Ghanés'),
        ('Kenia', 'Kenia'),
        ('Keniano', 'Keniano'),
        ('Tanzano', 'Tanzano'),
        ('Ugandés', 'Ugandés'),
        ('Etíope', 'Etíope'),
        ('Camerunés', 'Camerunés'),
        ('Senegalés', 'Senegalés'),
        ('Israelí', 'Israelí'),
        ('Jordano', 'Jordano'),
        ('Sirio', 'Sirio'),
        ('Irakí', 'Irakí'),
        ('Iraní', 'Iraní'),
        ('Arabe', 'Arabe'),
        ('Saudí', 'Saudí'),
        ('Emiratí', 'Emiratí'),
        ('Pakistaní', 'Pakistaní'),
        ('Indio', 'Indio'),
        ('Bangladesí', 'Bangladesí'),
        ('Sri Lanka', 'Sri Lanka'),
        ('Srilanqués', 'Srilanqués'),
        ('Nepalí', 'Nepalí'),
        ('Chino', 'Chino'),
        ('Japonés', 'Japonés'),
        ('Coreano', 'Coreano'),
        ('Filipino', 'Filipino'),
        ('Vietnamita', 'Vietnamita'),
        ('Tailandés', 'Tailandés'),
        ('Malayo', 'Malayo'),
        ('Indonesio', 'Indonesio'),
        ('Singapurense', 'Singapurense'),
        ('Australiano', 'Australiano'),
        ('Neozelandés', 'Neozelandés'),
        ('Otro', 'Otro'),
    ]
    NACIONALIDADES_CHOICES = tuple(
        sorted(_NACIONALIDADES_RAW, key=lambda item: item[1].casefold())
    )

    # Sexo del huésped (para DNI peruanos y uso general).
    SEXO_MASCULINO = 'M'
    SEXO_FEMENINO = 'F'
    SEXO_OTRO = 'O'
    SEXO_PREFER_NO = 'N'
    SEXO_CHOICES = [
        (SEXO_MASCULINO, 'Masculino'),
        (SEXO_FEMENINO, 'Femenino'),
        (SEXO_OTRO, 'Otro'),
        (SEXO_PREFER_NO, 'Prefiero no decir'),
    ]

    MOTIVO_VIAJE_TURISMO = 'turismo'
    MOTIVO_VIAJE_NEGOCIOS = 'negocios'
    MOTIVO_VIAJE_TRABAJO = 'trabajo'
    MOTIVO_VIAJE_ESTUDIOS = 'estudios'
    MOTIVO_VIAJE_VISITA_FAMILIAR = 'visita_familiar'
    MOTIVO_VIAJE_SALUD = 'salud'
    MOTIVO_VIAJE_CHOICES = [
        (MOTIVO_VIAJE_TURISMO, 'Turismo'),
        (MOTIVO_VIAJE_NEGOCIOS, 'Negocios'),
        (MOTIVO_VIAJE_TRABAJO, 'Trabajo'),
        (MOTIVO_VIAJE_ESTUDIOS, 'Estudios'),
        (MOTIVO_VIAJE_VISITA_FAMILIAR, 'Visita familiar'),
        (MOTIVO_VIAJE_SALUD, 'Salud'),
    ]

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='huespedes',
        verbose_name='Hotel',
    )

    # ========== CAMPOS DE IDENTIFICACIÓN PERSONAL ==========

    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombres',
        help_text='Nombres del huésped'
    )

    apellidos = models.CharField(
        max_length=100,
        verbose_name='Apellidos',
        help_text='Apellidos del huésped'
    )

    tipo_documento = models.CharField(
        max_length=30,
        choices=TIPO_DOCUMENTO_CHOICES,
        default=TIPO_DOC_DNI,
        verbose_name='Tipo de documento',
        help_text='DNI para peruanos; CE, pasaporte u otro para extranjeros.',
    )

    documento_identidad = models.CharField(
        max_length=50,
        verbose_name='Número de documento',
        help_text='Número del DNI, CE, pasaporte, etc. (único por hotel junto al tipo)',
    )

    lugar_residencia = models.CharField(
        max_length=200,
        verbose_name='Lugar de residencia',
        help_text='Ciudad o lugar de residencia habitual del huésped',
    )

    motivo_viaje = models.CharField(
        max_length=30,
        choices=MOTIVO_VIAJE_CHOICES,
        default=MOTIVO_VIAJE_TURISMO,
        verbose_name='Motivo de viaje',
    )

    fecha_nacimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Nacimiento'
    )
    
    nacionalidad = models.CharField(
        max_length=100,
        default='Perú',
        verbose_name='Nacionalidad'
    )

    sexo = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=SEXO_CHOICES,
        verbose_name='Sexo',
    )

    # ========== CAMPOS DE AUDITORÍA ==========
    
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Registro'
    )
    
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Actualización'
    )

    objects = TenantScopedManager()
    all_objects = AllObjectsManager()

    # ========== META Y MÉTODOS ==========

    class Meta:
        verbose_name = 'Huésped'
        verbose_name_plural = 'Huéspedes'
        ordering = ['apellidos', 'nombre']
        base_manager_name = 'all_objects'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'tipo_documento', 'documento_identidad'],
                name='uniq_huesped_tenant_tipo_documento',
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'tipo_documento', 'documento_identidad']),
            models.Index(fields=['apellidos', 'nombre']),
        ]

    def save(self, *args, **kwargs):
        t = get_current_tenant()
        if t is not None and self.tenant_id is None:
            self.tenant = t
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre} {self.apellidos}'
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del huésped"""
        return f'{self.nombre} {self.apellidos}'

    def etiqueta_documento_resumida(self):
        """Texto corto para listados (ej. DNI, CE)."""
        cortos = {
            self.TIPO_DOC_DNI: 'DNI',
            self.TIPO_DOC_CARNET_EXTRANJERIA: 'CE',
            self.TIPO_DOC_PASAPORTE: 'Pasaporte',
            self.TIPO_DOC_OTRO: 'Doc.',
        }
        return cortos.get(self.tipo_documento, 'Doc.')


class Reserva(models.Model):
    """
    Modelo que representa una reserva de habitación.

    Conecta un huésped con una habitación para un período específico.
    El precio se calcula automáticamente basado en las noches y el precio de la habitación.
    """

    # ========== CONSTANTES Y CHOICES ==========
    
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_CONFIRMADA = 'confirmada'
    ESTADO_CHECKIN = 'checkin'
    ESTADO_CHECKOUT = 'checkout'
    ESTADO_CANCELADA = 'cancelada'
    
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_CONFIRMADA, 'Confirmada'),
        (ESTADO_CHECKIN, 'Check-in Realizado'),
        (ESTADO_CHECKOUT, 'Check-out Realizado'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    # Estadía por noches: salida máxima el día `fecha_salida` a esta hora (zona del hotel).
    HORA_LIMITE_CHECKOUT_NOCHE = time(12, 0)

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name='Hotel',
    )

    # ========== RELACIONES (Foreign Keys) ==========

    huesped = models.ForeignKey(
        Huesped,
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name='Huésped',
        help_text='Huésped que realiza la reserva'
    )
    
    habitacion = models.ForeignKey(
        Habitacion,
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name='Habitación',
        help_text='Habitación reservada'
    )
    
    # ========== CAMPOS DE FECHAS ==========
    
    fecha_entrada = models.DateField(
        verbose_name='Fecha de Entrada',
        help_text='Fecha en que el huésped ingresará al hotel'
    )
    
    fecha_salida = models.DateField(
        verbose_name='Fecha de Salida',
        help_text=(
            'Día de checkout. Con política por noches, la salida máxima es ese día a las 12:00 (mediodía). '
            'Ej.: 1 noche = entrada un día y salida el día siguiente hasta mediodía.'
        ),
    )

    fecha_hora_salida_prevista = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Salida prevista (fecha y hora)',
        help_text=(
            'Opcional: para estadías cortas por horas (walk-in u otras), hora prevista de check-out. '
            'Si no aplica, quede vacío y se usa solo la fecha de salida.'
        ),
    )
    
    # ========== CAMPOS DE LA RESERVA ==========
    
    numero_huespedes = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Número de Huéspedes',
        help_text='Cantidad de personas que se alojarán'
    )
    
    precio_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Precio total (soles)',
        help_text='Total en soles (noches × precio/noche)'
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
        verbose_name='Estado',
        help_text='Estado actual de la reserva'
    )
    
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Notas adicionales sobre la reserva'
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reservas_creadas',
        verbose_name='Creada por',
        help_text='Usuario (p. ej. administrador o recepción) que registró la reserva en el sistema.',
    )
    
    # ========== CAMPOS DE AUDITORÍA ==========
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Actualización'
    )

    objects = TenantScopedManager()
    all_objects = AllObjectsManager()

    # ========== META Y MÉTODOS ==========

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-fecha_creacion']
        base_manager_name = 'all_objects'
        indexes = [
            models.Index(fields=['fecha_entrada', 'fecha_salida']),
            models.Index(fields=['estado']),
            models.Index(fields=['huesped']),
            models.Index(fields=['habitacion']),
            models.Index(fields=['tenant', 'estado']),
            # Consultas por hotel + rango de fechas / listados recientes (muchos tenants).
            models.Index(fields=['tenant', 'fecha_entrada', 'fecha_salida']),
            models.Index(fields=['tenant', 'fecha_creacion']),
        ]

    def __str__(self):
        return f'Reserva #{self.id} - {self.huesped.nombre_completo} - Hab. {self.habitacion.numero}'
    
    @property
    def numero_noches(self):
        """
        Calcula el número de noches de la reserva.
        
        Returns:
            int: Número de noches entre fecha_entrada y fecha_salida
        """
        if self.fecha_entrada and self.fecha_salida:
            return (self.fecha_salida - self.fecha_entrada).days
        return 0

    @property
    def es_estadia_por_horas(self):
        """True si hay salida prevista con hora (estadía corta, típico walk-in)."""
        return self.fecha_hora_salida_prevista is not None

    def descripcion_salida_prevista(self):
        """Texto para UI: hora de salida prevista o vacío."""
        if not self.fecha_hora_salida_prevista:
            return ''
        return timezone.localtime(self.fecha_hora_salida_prevista).strftime('%d/%m/%Y %H:%M')

    def fecha_hora_limite_checkout_local(self):
        """
        Momento límite de estadía según política del hotel (zona TIME_ZONE).
        Por noches: mediodía del día `fecha_salida`. Por horas: `fecha_hora_salida_prevista`.
        """
        if self.fecha_hora_salida_prevista:
            return self.fecha_hora_salida_prevista
        if self.fecha_salida:
            tz = timezone.get_default_timezone()
            naive = datetime.combine(self.fecha_salida, self.HORA_LIMITE_CHECKOUT_NOCHE)
            return timezone.make_aware(naive, tz)
        return None

    def texto_politica_salida(self):
        """Una línea para recepción y detalle de reserva."""
        if self.fecha_hora_salida_prevista:
            return f'Salida prevista: {self.descripcion_salida_prevista()}'
        lim = self.fecha_hora_limite_checkout_local()
        if not lim:
            return ''
        return timezone.localtime(lim).strftime(
            'Salida máxima: %d/%m/%Y a las %H:%M (12:00 mediodía, día de checkout)'
        )

    def horas_desde_checkin_hasta_salida_prevista(self):
        """Horas entre el check-in real y la salida prevista; None si no aplica."""
        if not self.fecha_hora_salida_prevista:
            return None
        try:
            ini = self.checkin.fecha_hora
        except ObjectDoesNotExist:
            return None
        secs = (self.fecha_hora_salida_prevista - ini).total_seconds()
        if secs <= 0:
            return 0.0
        return round(secs / 3600, 2)
    
    def calcular_precio_total(self):
        """
        Calcula el precio total basado en las noches y el precio de la habitación,
        o proporcional por horas si hay salida prevista sin noches completas.
        
        Returns:
            Decimal: Precio total calculado
        """
        from decimal import Decimal

        if not self.habitacion_id:
            return Decimal('0')

        if self.fecha_hora_salida_prevista:
            try:
                ini = self.checkin.fecha_hora
            except ObjectDoesNotExist:
                ini = timezone.now()
            fin = self.fecha_hora_salida_prevista
            if fin > ini:
                horas = Decimal(str((fin - ini).total_seconds())) / Decimal(3600)
                horas = max(horas, Decimal('1') / Decimal(60))
                proporcional = (self.habitacion.precio_noche * (horas / Decimal(24))).quantize(
                    Decimal('0.01')
                )
                minimo_corta = (self.habitacion.precio_noche * Decimal('0.15')).quantize(
                    Decimal('0.01')
                )
                return max(proporcional, minimo_corta)

        if self.fecha_entrada and self.fecha_salida and self.habitacion:
            noches = self.numero_noches
            if noches > 0:
                return noches * self.habitacion.precio_noche
        return Decimal('0')
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para calcular automáticamente el precio_total
        si no está definido o es cero, y alinear tenant con la habitación.
        """
        if self.habitacion_id:
            self.tenant_id = self.habitacion.tenant_id
        if not self.precio_total or self.precio_total == 0:
            self.precio_total = self.calcular_precio_total()
        super().save(*args, **kwargs)


def _validar_desglose_cuatro_medios(total, efectivo, tarjeta, yape, transferencia):
    """
    Valida que cuatro montos no negativos sumen `total` y que al menos dos medios tengan monto > 0.
    Usado en check-out (pago mixto) y check-in (depósito mixto).
    Devuelve mensaje de error (str) o None.
    """
    q = Decimal('0.01')
    total_q = (total or Decimal('0')).quantize(q)
    e = (efectivo or Decimal('0')).quantize(q)
    ta = (tarjeta or Decimal('0')).quantize(q)
    y = (yape or Decimal('0')).quantize(q)
    tr = (transferencia or Decimal('0')).quantize(q)
    soma = (e + ta + y + tr).quantize(q)
    if soma != total_q:
        return 'La suma de efectivo, tarjeta, Yape y transferencia debe ser igual al monto total indicado.'
    medios_con_monto = sum(1 for x in (e, ta, y, tr) if x > 0)
    if medios_con_monto < 2:
        return 'Indique al menos dos medios con monto mayor a cero (por ejemplo efectivo y Yape).'
    return None


class CheckIn(models.Model):
    """
    Modelo que representa el registro de check-in de una reserva.
    
    Se crea cuando un huésped ingresa al hotel y se registra su llegada.
    Tiene relación OneToOne con Reserva (una reserva tiene un solo check-in).
    """
    
    # ========== RELACIÓN ==========
    
    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='checkin',
        verbose_name='Reserva',
        help_text='Reserva asociada al check-in'
    )
    
    # ========== CAMPOS DE REGISTRO ==========
    
    fecha_hora = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha y Hora',
        help_text='Fecha y hora en que se realizó el check-in'
    )
    
    empleado = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Empleado',
        help_text='Nombre del empleado que realizó el check-in'
    )
    
    documentos_recibidos = models.BooleanField(
        default=False,
        verbose_name='Documentos Recibidos',
        help_text='Indica si se recibieron los documentos de identidad'
    )

    DEPOSITO_EFECTIVO = 'efectivo'
    DEPOSITO_YAPE = 'yape'
    DEPOSITO_TRANSFERENCIA = 'transferencia'
    DEPOSITO_MIXTO = 'mixto'
    METODO_DEPOSITO_CHOICES = [
        (DEPOSITO_EFECTIVO, 'Efectivo'),
        (DEPOSITO_YAPE, 'Yape'),
        (DEPOSITO_TRANSFERENCIA, 'Transferencia'),
        (DEPOSITO_MIXTO, 'Mixto'),
    ]

    deposito = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Depósito',
        help_text='Depósito recibido al momento del check-in'
    )

    metodo_deposito = models.CharField(
        max_length=20,
        choices=METODO_DEPOSITO_CHOICES,
        blank=True,
        null=True,
        verbose_name='Método del depósito',
        help_text='Cómo se recibió el depósito (incluye mixto con desglose)',
    )

    mixto_efectivo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Dep. mixto — efectivo',
        help_text='Parte en efectivo cuando el depósito es mixto',
    )
    mixto_tarjeta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Dep. mixto — tarjeta',
        help_text='Parte con tarjeta cuando el depósito es mixto',
    )
    mixto_yape = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Dep. mixto — Yape',
        help_text='Parte por Yape cuando el depósito es mixto',
    )
    mixto_transferencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Dep. mixto — transferencia',
        help_text='Parte por transferencia cuando el depósito es mixto',
    )
    
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Notas adicionales del check-in'
    )

    objects = ThroughReservaTenantManager()
    all_objects = AllObjectsManager()

    # ========== META Y MÉTODOS ==========

    class Meta:
        verbose_name = 'Check-in'
        verbose_name_plural = 'Check-ins'
        ordering = ['-fecha_hora']
        base_manager_name = 'all_objects'
        indexes = [
            models.Index(fields=['fecha_hora']),
        ]

    def __str__(self):
        return f'Check-in Reserva #{self.reserva.id} - {self.fecha_hora.strftime("%Y-%m-%d %H:%M")}'

    @classmethod
    def validar_desglose_mixto_deposito(cls, total_deposito, efectivo, tarjeta, yape, transferencia):
        return _validar_desglose_cuatro_medios(total_deposito, efectivo, tarjeta, yape, transferencia)

    @property
    def desglose_deposito_mixto_partes(self):
        if self.metodo_deposito != self.DEPOSITO_MIXTO:
            return []
        pares = [
            ('Efectivo', self.mixto_efectivo or Decimal('0')),
            ('Tarjeta', self.mixto_tarjeta or Decimal('0')),
            ('Yape', self.mixto_yape or Decimal('0')),
            ('Transferencia', self.mixto_transferencia or Decimal('0')),
        ]
        return [(lbl, m) for lbl, m in pares if m > 0]

    def clean(self):
        super().clean()
        dep = self.deposito or Decimal('0')
        if dep <= 0:
            return
        if not self.metodo_deposito:
            raise ValidationError(
                {'metodo_deposito': ['Si hay depósito, indique el método (o mixto con desglose).']}
            )
        if self.metodo_deposito != self.DEPOSITO_MIXTO:
            return
        err = _validar_desglose_cuatro_medios(
            dep,
            self.mixto_efectivo,
            self.mixto_tarjeta,
            self.mixto_yape,
            self.mixto_transferencia,
        )
        if err:
            raise ValidationError({'mixto_efectivo': [err]})

    def save(self, *args, **kwargs):
        dep = self.deposito or Decimal('0')
        if dep > 0 and not self.metodo_deposito:
            raise ValidationError(
                {'metodo_deposito': ['Si hay depósito, indique el método (o mixto con desglose).']}
            )
        if self.deposito <= 0:
            self.metodo_deposito = None
            self.mixto_efectivo = Decimal('0')
            self.mixto_tarjeta = Decimal('0')
            self.mixto_yape = Decimal('0')
            self.mixto_transferencia = Decimal('0')
        elif self.metodo_deposito != self.DEPOSITO_MIXTO:
            self.mixto_efectivo = Decimal('0')
            self.mixto_tarjeta = Decimal('0')
            self.mixto_yape = Decimal('0')
            self.mixto_transferencia = Decimal('0')
        super().save(*args, **kwargs)


class CheckOut(models.Model):
    """
    Modelo que representa el registro de check-out de una reserva.
    
    Se crea cuando un huésped sale del hotel y se registra su salida,
    incluyendo el pago final y evaluación del servicio.
    Tiene relación OneToOne con Reserva (una reserva tiene un solo check-out).
    """
    
    # ========== CONSTANTES Y CHOICES ==========
    
    METODO_EFECTIVO = 'efectivo'
    METODO_TARJETA = 'tarjeta'
    METODO_YAPE = 'yape'
    METODO_TRANSFERENCIA = 'transferencia'
    METODO_MIXTO = 'mixto'
    
    METODO_PAGO_CHOICES = [
        (METODO_EFECTIVO, 'Efectivo'),
        (METODO_TARJETA, 'Tarjeta'),
        (METODO_YAPE, 'Yape'),
        (METODO_TRANSFERENCIA, 'Transferencia'),
        (METODO_MIXTO, 'Mixto'),
    ]
    
    # ========== RELACIÓN ==========
    
    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='checkout',
        verbose_name='Reserva',
        help_text='Reserva asociada al check-out'
    )
    
    # ========== CAMPOS DE REGISTRO ==========
    
    fecha_hora = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha y Hora',
        help_text='Fecha y hora en que se realizó el check-out'
    )

    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checkouts_registrados',
        verbose_name='Registrado por',
        help_text='Usuario de la cuenta que registró el check-out',
    )

    # ========== CAMPOS DE PAGO ==========
    
    total_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Total Pagado',
        help_text='Monto total pagado al momento del check-out'
    )
    
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default=METODO_EFECTIVO,
        verbose_name='Método de Pago',
        help_text='Método utilizado para el pago'
    )

    mixto_efectivo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Mixto — efectivo',
        help_text='Parte en efectivo cuando el pago es mixto',
    )
    mixto_tarjeta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Mixto — tarjeta',
        help_text='Parte con tarjeta cuando el pago es mixto',
    )
    mixto_yape = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Mixto — Yape',
        help_text='Parte por Yape cuando el pago es mixto',
    )
    mixto_transferencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Mixto — transferencia',
        help_text='Parte por transferencia cuando el pago es mixto',
    )
    
    # ========== CAMPOS DE EVALUACIÓN ==========
    
    danos_observados = models.TextField(
        blank=True,
        verbose_name='Daños Observados',
        help_text='Descripción de daños o problemas encontrados en la habitación'
    )
    
    calificacion = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name='Calificación',
        help_text='Calificación del servicio (1-5)'
    )
    
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Notas adicionales del check-out'
    )

    objects = ThroughReservaTenantManager()
    all_objects = AllObjectsManager()

    # ========== META Y MÉTODOS ==========

    class Meta:
        verbose_name = 'Check-out'
        verbose_name_plural = 'Check-outs'
        ordering = ['-fecha_hora']
        base_manager_name = 'all_objects'
        indexes = [
            models.Index(fields=['fecha_hora']),
            models.Index(fields=['metodo_pago']),
        ]

    def __str__(self):
        return f'Check-out Reserva #{self.reserva.id} - {self.fecha_hora.strftime("%Y-%m-%d %H:%M")}'

    @classmethod
    def validar_desglose_mixto(cls, total_pagado, efectivo, tarjeta, yape, transferencia):
        """Valida montos del desglose cuando metodo_pago es mixto."""
        return _validar_desglose_cuatro_medios(total_pagado, efectivo, tarjeta, yape, transferencia)

    def desglose_mixto_partes(self):
        """Pares (etiqueta, monto) con monto > 0; vacío si no aplica."""
        if self.metodo_pago != self.METODO_MIXTO:
            return []
        pares = [
            ('Efectivo', self.mixto_efectivo or Decimal('0')),
            ('Tarjeta', self.mixto_tarjeta or Decimal('0')),
            ('Yape', self.mixto_yape or Decimal('0')),
            ('Transferencia', self.mixto_transferencia or Decimal('0')),
        ]
        return [(lbl, m) for lbl, m in pares if m > 0]

    def clean(self):
        super().clean()
        if self.metodo_pago != self.METODO_MIXTO:
            return
        err = self.validar_desglose_mixto(
            self.total_pagado,
            self.mixto_efectivo,
            self.mixto_tarjeta,
            self.mixto_yape,
            self.mixto_transferencia,
        )
        if err:
            raise ValidationError({'mixto_efectivo': [err]})

    def save(self, *args, **kwargs):
        if self.metodo_pago != self.METODO_MIXTO:
            self.mixto_efectivo = Decimal('0')
            self.mixto_tarjeta = Decimal('0')
            self.mixto_yape = Decimal('0')
            self.mixto_transferencia = Decimal('0')
        super().save(*args, **kwargs)
