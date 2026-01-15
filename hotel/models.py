"""
Modelos del Sistema Hotelero

Este módulo contiene todos los modelos de datos del sistema:
- Habitacion: Representa las habitaciones del hotel
- Huesped: Representa a los huéspedes/clientes
- Reserva: Representa las reservas realizadas
- CheckIn: Registro de check-in de una reserva
- CheckOut: Registro de check-out de una reserva
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


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
    
    TIPO_SENCILLA = 'sencilla'
    TIPO_DOBLE = 'doble'
    TIPO_SUITE = 'suite'
    TIPO_PRESIDENCIAL = 'presidencial'
    
    TIPO_CHOICES = [
        (TIPO_SENCILLA, 'Sencilla'),
        (TIPO_DOBLE, 'Doble'),
        (TIPO_SUITE, 'Suite'),
        (TIPO_PRESIDENCIAL, 'Presidencial'),
    ]
    
    # ========== CAMPOS BÁSICOS (Identificación) ==========
    
    numero = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Número de Habitación',
        help_text='Número único que identifica la habitación'
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
        verbose_name='Precio por Noche',
        help_text='Precio base por noche en la moneda local'
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
    
    # ========== META Y MÉTODOS ==========
    
    class Meta:
        verbose_name = 'Habitación'
        verbose_name_plural = 'Habitaciones'
        ordering = ['numero']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['estado']),
            models.Index(fields=['tipo']),
        ]
    
    def __str__(self):
        return f'Habitación {self.numero} - {self.get_tipo_display()}'


class Huesped(models.Model):
    """
    Modelo que representa a un huésped (cliente) del hotel.
    
    Almacena información personal, de contacto y preferencias
    del huésped para mejorar el servicio.
    """
    
    # ========== CAMPOS DE IDENTIFICACIÓN PERSONAL ==========
    
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre',
        help_text='Nombre(s) del huésped'
    )
    
    apellidos = models.CharField(
        max_length=100,
        verbose_name='Apellidos',
        help_text='Apellidos del huésped'
    )
    
    documento_identidad = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Documento de Identidad',
        help_text='Pasaporte, DNI, CURP u otro documento oficial'
    )
    
    fecha_nacimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Nacimiento'
    )
    
    nacionalidad = models.CharField(
        max_length=100,
        default='México',
        verbose_name='Nacionalidad'
    )
    
    # ========== CAMPOS DE CONTACTO ==========
    
    email = models.EmailField(
        verbose_name='Email',
        help_text='Correo electrónico de contacto'
    )
    
    telefono = models.CharField(
        max_length=20,
        verbose_name='Teléfono',
        help_text='Número de teléfono de contacto'
    )
    
    # ========== CAMPOS OPCIONALES (Preferencias y Notas) ==========
    
    preferencias = models.TextField(
        blank=True,
        verbose_name='Preferencias',
        help_text='Preferencias especiales del huésped (cama extra, piso alto, etc.)'
    )
    
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Notas adicionales sobre el huésped'
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
    
    # ========== META Y MÉTODOS ==========
    
    class Meta:
        verbose_name = 'Huésped'
        verbose_name_plural = 'Huéspedes'
        ordering = ['apellidos', 'nombre']
        indexes = [
            models.Index(fields=['documento_identidad']),
            models.Index(fields=['apellidos', 'nombre']),
        ]
    
    def __str__(self):
        return f'{self.nombre} {self.apellidos}'
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del huésped"""
        return f'{self.nombre} {self.apellidos}'


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
        help_text='Fecha en que el huésped saldrá del hotel'
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
        verbose_name='Precio Total',
        help_text='Precio total calculado automáticamente (noches × precio/noche)'
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
    
    # ========== CAMPOS DE AUDITORÍA ==========
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Fecha de Actualización'
    )
    
    # ========== META Y MÉTODOS ==========
    
    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['fecha_entrada', 'fecha_salida']),
            models.Index(fields=['estado']),
            models.Index(fields=['huesped']),
            models.Index(fields=['habitacion']),
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
    
    def calcular_precio_total(self):
        """
        Calcula el precio total basado en las noches y el precio de la habitación.
        
        Returns:
            Decimal: Precio total calculado
        """
        if self.fecha_entrada and self.fecha_salida and self.habitacion:
            noches = self.numero_noches
            if noches > 0:
                return noches * self.habitacion.precio_noche
        return 0
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para calcular automáticamente el precio_total
        si no está definido o es cero.
        """
        if not self.precio_total or self.precio_total == 0:
            self.precio_total = self.calcular_precio_total()
        super().save(*args, **kwargs)


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
    
    deposito = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Depósito',
        help_text='Depósito recibido al momento del check-in'
    )
    
    notas = models.TextField(
        blank=True,
        verbose_name='Notas',
        help_text='Notas adicionales del check-in'
    )
    
    # ========== META Y MÉTODOS ==========
    
    class Meta:
        verbose_name = 'Check-in'
        verbose_name_plural = 'Check-ins'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['fecha_hora']),
        ]
    
    def __str__(self):
        return f'Check-in Reserva #{self.reserva.id} - {self.fecha_hora.strftime("%Y-%m-%d %H:%M")}'


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
    METODO_TRANSFERENCIA = 'transferencia'
    METODO_MIXTO = 'mixto'
    
    METODO_PAGO_CHOICES = [
        (METODO_EFECTIVO, 'Efectivo'),
        (METODO_TARJETA, 'Tarjeta'),
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
    
    empleado = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Empleado',
        help_text='Nombre del empleado que realizó el check-out'
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
    
    # ========== META Y MÉTODOS ==========
    
    class Meta:
        verbose_name = 'Check-out'
        verbose_name_plural = 'Check-outs'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['fecha_hora']),
            models.Index(fields=['metodo_pago']),
        ]
    
    def __str__(self):
        return f'Check-out Reserva #{self.reserva.id} - {self.fecha_hora.strftime("%Y-%m-%d %H:%M")}'
