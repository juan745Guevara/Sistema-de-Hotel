from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Habitacion(models.Model):
    """Modelo para representar las habitaciones del hotel"""
    
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('ocupada', 'Ocupada'),
        ('mantenimiento', 'En Mantenimiento'),
        ('limpieza', 'En Limpieza'),
        ('reservada', 'Reservada'),
    ]
    
    TIPO_CHOICES = [
        ('sencilla', 'Sencilla'),
        ('doble', 'Doble'),
        ('suite', 'Suite'),
        ('presidencial', 'Presidencial'),
    ]
    
    numero = models.CharField(max_length=10, unique=True, verbose_name='Número de Habitación')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible', verbose_name='Estado')
    capacidad = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Capacidad (personas)')
    precio_noche = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Precio por Noche')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    servicios = models.TextField(blank=True, help_text='Servicios incluidos (WiFi, TV, etc.)', verbose_name='Servicios')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Habitación'
        verbose_name_plural = 'Habitaciones'
        ordering = ['numero']
    
    def __str__(self):
        return f'Habitación {self.numero} - {self.get_tipo_display()}'


class Huesped(models.Model):
    """Modelo para representar a los huéspedes del hotel"""
    
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    email = models.EmailField(verbose_name='Email')
    telefono = models.CharField(max_length=20, verbose_name='Teléfono')
    documento_identidad = models.CharField(max_length=50, unique=True, verbose_name='Documento de Identidad')
    nacionalidad = models.CharField(max_length=100, default='México', verbose_name='Nacionalidad')
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name='Fecha de Nacimiento')
    preferencias = models.TextField(blank=True, help_text='Preferencias especiales del huésped', verbose_name='Preferencias')
    notas = models.TextField(blank=True, verbose_name='Notas')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Huésped'
        verbose_name_plural = 'Huéspedes'
        ordering = ['apellidos', 'nombre']
    
    def __str__(self):
        return f'{self.nombre} {self.apellidos}'
    
    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellidos}'


class Reserva(models.Model):
    """Modelo para representar las reservas del hotel"""
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('checkin', 'Check-in Realizado'),
        ('checkout', 'Check-out Realizado'),
        ('cancelada', 'Cancelada'),
    ]
    
    huesped = models.ForeignKey(Huesped, on_delete=models.CASCADE, related_name='reservas', verbose_name='Huésped')
    habitacion = models.ForeignKey(Habitacion, on_delete=models.CASCADE, related_name='reservas', verbose_name='Habitación')
    fecha_entrada = models.DateField(verbose_name='Fecha de Entrada')
    fecha_salida = models.DateField(verbose_name='Fecha de Salida')
    numero_huespedes = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Número de Huéspedes')
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Precio Total')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name='Estado')
    notas = models.TextField(blank=True, verbose_name='Notas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f'Reserva #{self.id} - {self.huesped.nombre_completo} - Hab. {self.habitacion.numero}'
    
    def calcular_precio_total(self):
        """Calcula el precio total basado en las noches y el precio de la habitación"""
        if self.fecha_entrada and self.fecha_salida:
            noches = (self.fecha_salida - self.fecha_entrada).days
            if noches > 0:
                return noches * self.habitacion.precio_noche
        return 0
    
    def save(self, *args, **kwargs):
        if not self.precio_total or self.precio_total == 0:
            self.precio_total = self.calcular_precio_total()
        super().save(*args, **kwargs)
    
    @property
    def numero_noches(self):
        """Calcula el número de noches de la reserva"""
        if self.fecha_entrada and self.fecha_salida:
            return (self.fecha_salida - self.fecha_entrada).days
        return 0


class CheckIn(models.Model):
    """Modelo para representar los check-ins realizados"""
    
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='checkin', verbose_name='Reserva')
    fecha_hora = models.DateTimeField(default=timezone.now, verbose_name='Fecha y Hora')
    empleado = models.CharField(max_length=100, blank=True, verbose_name='Empleado que realizó el check-in')
    notas = models.TextField(blank=True, verbose_name='Notas')
    documentos_recibidos = models.BooleanField(default=False, verbose_name='Documentos Recibidos')
    deposito = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name='Depósito')
    
    class Meta:
        verbose_name = 'Check-in'
        verbose_name_plural = 'Check-ins'
        ordering = ['-fecha_hora']
    
    def __str__(self):
        return f'Check-in Reserva #{self.reserva.id} - {self.fecha_hora.strftime("%Y-%m-%d %H:%M")}'


class CheckOut(models.Model):
    """Modelo para representar los check-outs realizados"""
    
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('mixto', 'Mixto'),
    ]
    
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='checkout', verbose_name='Reserva')
    fecha_hora = models.DateTimeField(default=timezone.now, verbose_name='Fecha y Hora')
    empleado = models.CharField(max_length=100, blank=True, verbose_name='Empleado que realizó el check-out')
    total_pagado = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Total Pagado')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='efectivo', verbose_name='Método de Pago')
    notas = models.TextField(blank=True, verbose_name='Notas')
    danos_observados = models.TextField(blank=True, verbose_name='Daños Observados')
    calificacion = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)], verbose_name='Calificación (1-5)')
    
    class Meta:
        verbose_name = 'Check-out'
        verbose_name_plural = 'Check-outs'
        ordering = ['-fecha_hora']
    
    def __str__(self):
        return f'Check-out Reserva #{self.reserva.id} - {self.fecha_hora.strftime("%Y-%m-%d %H:%M")}'

