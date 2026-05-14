# Sistema Hotelero (HotelFlow)

Aplicación web de gestión hotelera con **Django 4.2**, multi-hotel (tenant), roles por hotel y flujos de recepción (reservas, walk-in, check-in/out, reportes).

## Requisitos

| Componente | Versión recomendada |
|------------|---------------------|
| Python | 3.10 o superior (compatible con Django 4.2) |
| Base de datos | SQLite por defecto; **PostgreSQL** opcional vía `.env` |
| Navegador | Moderno (ES6; Bootstrap 5) |

Las dependencias Python están en `requirements.txt`.

## Instalación rápida

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
```

Opcional: crea un archivo **`.env`** en la raíz del proyecto con variables como `SECRET_KEY`, `DEBUG`, `DATABASE_ENGINE`, `POSTGRES_*`, `SQLITE_NAME`, etc. El proyecto usa **python-decouple** para leerlas (por ejemplo `DATABASE_ENGINE=postgresql` junto con `POSTGRES_DB`, `POSTGRES_USER`, …).

```bash
python manage.py migrate
python manage.py createsuperuser   # acceso al admin de Django
python manage.py runserver
```

- **Aplicación:** http://127.0.0.1:8000/  
- **Admin:** http://127.0.0.1:8000/admin/  

El acceso al panel del hotel usa un flujo propio: identificación del hotel (slug) → usuario, rol y contraseña (`/accounts/hotel/`, etc.). La creación de hoteles o cuentas desde la web puede estar deshabilitada según la configuración; en muchos despliegues el alta se hace por consola.

## Características principales

### Multi-hotel y permisos

- Varios **hoteles (tenants)** en la misma base de datos; cada petición trabaja en el hotel activo de la sesión.
- **Usuarios y membresías** por hotel con roles (p. ej. administrador, recepción, limpieza) y permisos por vista.

### Recepción y operación

- **Dashboard** de recepción con tareas y accesos rápidos.
- **Reservas:** crear, editar, cancelar; validación de disponibilidad y capacidad; precios por noche; estadía por noches u horas según flujos soportados.
- **Walk-in:** check-in sin reserva previa con datos de huésped y habitación.
- **Check-in / check-out** (incluidos flujos rápidos y listas), depósitos y medios de pago (incl. mixtos donde aplique).
- **Huéspedes:** tipo de documento (DNI, CE, pasaporte, otro); **DNI Perú: 8 dígitos numéricos** (validación en servidor y restricción en formularios).
- **Habitaciones:** estados (disponible, ocupada, reservada, mantenimiento, limpieza), tipos y precios.
- **Búsqueda rápida** en cabecera (atajo tipo Ctrl+K según plantilla).
- **Calendario de ocupación** mensual.
- **Tablero de habitaciones** y lista de limpieza.

### Reportes

- **Estadísticas de ocupación** (cupo nocturno, evolución, comparación con periodo anterior, desglose por tipo).
- **Ingresos** (reservas por fecha de entrada, cobros por ventana de fecha/hora de turno, medios de pago, depósitos).
- **Libro de registro** con exportación a **PDF** (ReportLab).

### Interfaz

- **Bootstrap 5** + **Bootstrap Icons**; formularios con **django-crispy-forms** y **crispy-bootstrap5**.
- Pantallas de inicio de sesión con identidad visual (logo en `static/hotel/`).

## Configuración útil (`settings`)

- `TIME_ZONE`: por defecto `America/Lima`.
- `STATICFILES_DIRS`: carpeta `static/` del proyecto (incluye branding para login).
- Caché en memoria local (`LocMemCache`) para desarrollo.

Para **producción**: `DEBUG=False`, `SECRET_KEY` seguro, `ALLOWED_HOSTS`, HTTPS, base de datos adecuada (PostgreSQL recomendado con concurrencia) y `collectstatic` + servidor de archivos estáticos.

## Estructura del repositorio (resumen)

```
├── hotel/                 # App principal (modelos, vistas, formularios, URLs, PDF, tests)
├── hotel_sistema/       # Proyecto Django (settings, urls, wsgi)
├── templates/             # Plantillas globales y por app (`hotel/`, `hotel/accounts/`, …)
├── static/                # Estáticos de desarrollo (p. ej. logo)
├── manage.py
├── requirements.txt
└── README.md
```

## Comandos de utilidad

| Comando | Descripción |
|---------|-------------|
| `python manage.py test` | Suite de tests |
| `python manage.py check` | Comprobaciones del sistema Django |

Existen comandos de gestión en `hotel/management/commands/` (por ejemplo datos demo u operaciones de limpieza); revisa su ayuda con `python manage.py <comando> --help`.

## Licencia

Uso según la licencia indicada por los propietarios del repositorio (educativo, comercial u otro, si está definido en el proyecto).
