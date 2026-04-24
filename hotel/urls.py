from django.urls import path
from . import auth_views, views

urlpatterns = [
    path('accounts/hotel/', auth_views.accounts_hotel_identify, name='accounts_hotel_identify'),
    path('accounts/login/', auth_views.accounts_login, name='accounts_login'),
    path('accounts/signup/', auth_views.accounts_signup, name='accounts_signup'),
    path('accounts/logout/', auth_views.accounts_logout, name='accounts_logout'),
    path('accounts/select-tenant/', auth_views.select_tenant, name='select_tenant'),
    path(
        'accounts/ingreso/<slug:tenant_slug>/',
        auth_views.accounts_ingreso_con_hotel,
        name='accounts_ingreso_con_hotel',
    ),
    # Página principal (Dashboard de recepción)
    path('', views.index, name='index'),
    
    # ========== NUEVAS FUNCIONALIDADES DE RECEPCIÓN ==========
    path('recepcion/checkin-rapido/', views.checkin_rapido, name='checkin_rapido'),
    path('recepcion/checkout-rapido/', views.checkout_rapido, name='checkout_rapido'),
    path('recepcion/walkin/', views.walkin, name='walkin'),
    path('recepcion/tablero/', views.tablero_habitaciones, name='tablero_habitaciones'),
    path('recepcion/calendario/', views.calendario_ocupacion, name='calendario_ocupacion'),
    path('api/busqueda/', views.busqueda_rapida, name='busqueda_rapida'),
    
    # Reservas
    path('reservas/', views.lista_reservas, name='lista_reservas'),
    path('reservas/crear/', views.crear_reserva, name='crear_reserva'),
    path('reservas/<int:reserva_id>/', views.detalle_reserva, name='detalle_reserva'),
    path('reservas/<int:reserva_id>/editar/', views.editar_reserva, name='editar_reserva'),
    path('reservas/<int:reserva_id>/cancelar/', views.cancelar_reserva, name='cancelar_reserva'),
    
    # Habitaciones
    path('habitaciones/', views.lista_habitaciones, name='lista_habitaciones'),
    path('habitaciones/crear/', views.crear_habitacion, name='crear_habitacion'),
    path('habitaciones/<int:habitacion_id>/', views.detalle_habitacion, name='detalle_habitacion'),
    path('habitaciones/<int:habitacion_id>/editar/', views.editar_habitacion, name='editar_habitacion'),
    path(
        'habitaciones/<int:habitacion_id>/eliminar/',
        views.eliminar_habitacion,
        name='eliminar_habitacion',
    ),
    path(
        'habitaciones/<int:habitacion_id>/estado/',
        views.actualizar_estado_habitacion,
        name='actualizar_estado_habitacion',
    ),
    path('habitaciones/disponibilidad/', views.disponibilidad_habitaciones, name='disponibilidad_habitaciones'),
    
    # Check-in
    path('checkin/', views.lista_checkins, name='lista_checkins'),
    path('checkin/<int:reserva_id>/', views.realizar_checkin, name='realizar_checkin'),
    
    # Check-out
    path('checkout/', views.lista_checkouts, name='lista_checkouts'),
    path('checkout/<int:reserva_id>/', views.realizar_checkout, name='realizar_checkout'),
    
    # Equipo (solo administrador del hotel)
    path('equipo/', views.lista_equipo, name='lista_equipo'),
    path('equipo/nuevo/', views.crear_equipo, name='crear_equipo'),
    path('equipo/<int:membership_id>/eliminar/', views.eliminar_equipo, name='eliminar_equipo'),

    # Reportes
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/ocupacion/', views.reporte_ocupacion, name='reporte_ocupacion'),
    path('reportes/ingresos/', views.reporte_ingresos, name='reporte_ingresos'),
]


