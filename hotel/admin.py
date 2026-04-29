from django.contrib import admin

from .models import (
    CheckIn,
    CheckOut,
    Habitacion,
    Huesped,
    Membership,
    Reserva,
    Tenant,
)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'role', 'joined_at']
    list_filter = ['role', 'tenant']
    list_editable = ['role']
    search_fields = ['user__username', 'tenant__name']
    autocomplete_fields = ['user', 'tenant']


@admin.register(Habitacion)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'tenant', 'tipo', 'estado', 'capacidad', 'precio_noche']
    list_filter = ['tipo', 'estado', 'tenant']
    search_fields = ['numero', 'descripcion']

    def get_queryset(self, request):
        return Habitacion.all_objects.all()


@admin.register(Huesped)
class HuespedAdmin(admin.ModelAdmin):
    list_display = [
        'tipo_documento',
        'documento_identidad',
        'nombre',
        'apellidos',
        'lugar_procedencia',
        'tenant',
        'email',
        'telefono',
    ]
    search_fields = ['nombre', 'apellidos', 'email', 'documento_identidad', 'lugar_procedencia']

    def get_queryset(self, request):
        return Huesped.all_objects.all()


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'tenant',
        'huesped',
        'habitacion',
        'fecha_entrada',
        'fecha_salida',
        'fecha_hora_salida_prevista',
        'estado',
        'precio_total',
        'creado_por',
    ]
    list_filter = ['estado', 'fecha_entrada', 'fecha_salida', 'tenant']
    search_fields = ['huesped__nombre', 'huesped__apellidos', 'habitacion__numero']
    date_hierarchy = 'fecha_entrada'

    def get_queryset(self, request):
        return Reserva.all_objects.all()


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = [
        'reserva',
        'fecha_hora',
        'empleado',
        'deposito',
        'metodo_deposito',
        'desglose_deposito_mixto_admin',
        'documentos_recibidos',
    ]

    @admin.display(description='Desglose dep. mixto')
    def desglose_deposito_mixto_admin(self, obj):
        if obj.metodo_deposito != CheckIn.DEPOSITO_MIXTO:
            return '—'
        partes = obj.desglose_deposito_mixto_partes
        if not partes:
            return '—'
        return ' · '.join(f'{lbl} {m}' for lbl, m in partes)
    list_filter = ['fecha_hora', 'documentos_recibidos', 'metodo_deposito']
    search_fields = ['reserva__huesped__nombre', 'reserva__huesped__apellidos']

    def get_queryset(self, request):
        return CheckIn.all_objects.all()


@admin.register(CheckOut)
class CheckOutAdmin(admin.ModelAdmin):
    list_display = ['reserva', 'fecha_hora', 'registrado_por', 'total_pagado', 'metodo_pago', 'desglose_mixto_admin']

    @admin.display(description='Desglose mixto')
    def desglose_mixto_admin(self, obj):
        if obj.metodo_pago != CheckOut.METODO_MIXTO:
            return '—'
        partes = obj.desglose_mixto_partes()
        if not partes:
            return '—'
        return ' · '.join(f'{lbl} {m}' for lbl, m in partes)
    exclude = ['calificacion']
    list_filter = ['metodo_pago', 'fecha_hora']
    search_fields = ['reserva__huesped__nombre', 'reserva__huesped__apellidos']

    def get_queryset(self, request):
        return CheckOut.all_objects.all()
