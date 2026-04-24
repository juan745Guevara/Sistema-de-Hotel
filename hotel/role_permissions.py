"""
Mapa URL name → roles permitidos (Membership.role).
Si una vista nueva no aparece aquí, se permite a todos los roles con hotel activo.
"""
from typing import Optional

from .models import Membership

ADMIN = Membership.ROLE_ADMIN
REC = Membership.ROLE_RECEPCION
LIM = Membership.ROLE_LIMPIEZA

# Rutas con restricción explícita (cualquier otra ruta con nombre: acceso a todos los roles del hotel)
URL_ROLE_ACCESS = {
    'index': {ADMIN, REC, LIM},
    'checkin_rapido': {ADMIN, REC},
    'checkout_rapido': {ADMIN, REC},
    'walkin': {ADMIN, REC},
    'tablero_habitaciones': {ADMIN, REC, LIM},
    'calendario_ocupacion': {ADMIN, REC},
    'busqueda_rapida': {ADMIN, REC},
    'lista_reservas': {ADMIN, REC},
    'crear_reserva': {ADMIN, REC},
    'detalle_reserva': {ADMIN, REC},
    'editar_reserva': {ADMIN, REC},
    'cancelar_reserva': {ADMIN, REC},
    'lista_habitaciones': {ADMIN, REC, LIM},
    'crear_habitacion': {ADMIN},
    'detalle_habitacion': {ADMIN, REC, LIM},
    'editar_habitacion': {ADMIN},
    'eliminar_habitacion': {ADMIN},
    'disponibilidad_habitaciones': {ADMIN, REC},
    'lista_checkins': {ADMIN, REC},
    'realizar_checkin': {ADMIN, REC},
    'lista_checkouts': {ADMIN, REC},
    'realizar_checkout': {ADMIN, REC},
    'reportes': {ADMIN},
    'reporte_ocupacion': {ADMIN},
    'reporte_ingresos': {ADMIN},
    'actualizar_estado_habitacion': {ADMIN, LIM},
    'lista_equipo': {ADMIN},
    'crear_equipo': {ADMIN},
    'eliminar_equipo': {ADMIN},
}


def role_may_access(role: str, url_name: Optional[str]) -> bool:
    if url_name is None:
        return True
    allowed = URL_ROLE_ACCESS.get(url_name)
    if allowed is None:
        return True
    return role in allowed
