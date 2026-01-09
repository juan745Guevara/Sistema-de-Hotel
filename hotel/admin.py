from django.contrib import admin
from .models import Habitacion, Huesped, Reserva, CheckIn, CheckOut


@admin.register(Habitacion)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'tipo', 'estado', 'capacidad', 'precio_noche']
    list_filter = ['tipo', 'estado']
    search_fields = ['numero', 'descripcion']


@admin.register(Huesped)
class HuespedAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'apellidos', 'email', 'telefono', 'documento_identidad']
    search_fields = ['nombre', 'apellidos', 'email', 'documento_identidad']


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['id', 'huesped', 'habitacion', 'fecha_entrada', 'fecha_salida', 'estado', 'precio_total']
    list_filter = ['estado', 'fecha_entrada', 'fecha_salida']
    search_fields = ['huesped__nombre', 'huesped__apellidos', 'habitacion__numero']
    date_hierarchy = 'fecha_entrada'


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ['reserva', 'fecha_hora', 'empleado', 'documentos_recibidos']
    list_filter = ['fecha_hora', 'documentos_recibidos']
    search_fields = ['reserva__huesped__nombre', 'reserva__huesped__apellidos']


@admin.register(CheckOut)
class CheckOutAdmin(admin.ModelAdmin):
    list_display = ['reserva', 'fecha_hora', 'total_pagado', 'metodo_pago', 'calificacion']
    list_filter = ['metodo_pago', 'fecha_hora']
    search_fields = ['reserva__huesped__nombre', 'reserva__huesped__apellidos']

