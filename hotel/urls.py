from django.urls import path
from . import views

urlpatterns = [
    # Página principal
    path('', views.index, name='index'),
    
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
    path('habitaciones/disponibilidad/', views.disponibilidad_habitaciones, name='disponibilidad_habitaciones'),
    
    # Check-in
    path('checkin/', views.lista_checkins, name='lista_checkins'),
    path('checkin/<int:reserva_id>/', views.realizar_checkin, name='realizar_checkin'),
    
    # Check-out
    path('checkout/', views.lista_checkouts, name='lista_checkouts'),
    path('checkout/<int:reserva_id>/', views.realizar_checkout, name='realizar_checkout'),
    
    # Huéspedes
    path('huespedes/', views.lista_huespedes, name='lista_huespedes'),
    path('huespedes/crear/', views.crear_huesped, name='crear_huesped'),
    path('huespedes/<int:huesped_id>/', views.detalle_huesped, name='detalle_huesped'),
    path('huespedes/<int:huesped_id>/editar/', views.editar_huesped, name='editar_huesped'),
    
    # Reportes
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/ocupacion/', views.reporte_ocupacion, name='reporte_ocupacion'),
    path('reportes/ingresos/', views.reporte_ingresos, name='reporte_ingresos'),
    path('reportes/huespedes/', views.reporte_huespedes, name='reporte_huespedes'),
]

