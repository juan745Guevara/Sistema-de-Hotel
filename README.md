# Sistema Hotelero

Sistema de gestión hotelera desarrollado con Django y SQLite que soluciona los problemas principales de administración de hoteles.

## Características Principales

### 🚀 Funcionalidades de Recepción (Nuevas)

#### Dashboard de Recepción
- Vista general con tareas del día
- Check-ins y check-outs pendientes
- Estadísticas rápidas de habitaciones
- Acciones rápidas con botones grandes

#### Proceso Rápido de Registro
- **Registro Rápido**: Crear huésped + reserva + check-in en un solo paso
- **Autocompletado con RENIEC**: Ingrese DNI y autocompleta datos automáticamente
- **Walk-in**: Check-in sin reserva previa
- Validación inteligente de disponibilidad

#### Check-in/Check-out Rápido
- **Check-in Rápido**: Lista de pendientes con acción en 1 clic
- **Check-out Rápido**: Cálculo automático (precio - depósito)
- Formularios simplificados con campos esenciales
- Auto-completar empleado y fecha/hora

#### Búsqueda Global
- Búsqueda rápida en el header (Ctrl+K)
- Busca huéspedes, reservas y habitaciones
- Resultados instantáneos con enlaces directos

#### Vista de Habitaciones
- **Tablero Kanban**: Habitaciones organizadas por estado
- Vista visual con colores por estado
- Información rápida de cada habitación

#### Calendario de Ocupación
- Vista mensual de reservas
- Ver ocupación por día
- Navegación entre meses

### 1. Gestión de Reservas
- Crear, editar y cancelar reservas
- Validación automática de disponibilidad
- Cálculo automático de precios
- Estados de reserva (Pendiente, Confirmada, Check-in, Check-out, Cancelada)
- Filtros por estado y fechas

### 2. Control de Habitaciones y Disponibilidad
- Gestión completa de habitaciones
- Estados: Disponible, Ocupada, Reservada, Mantenimiento, Limpieza
- Verificación de disponibilidad en tiempo real
- Consulta de disponibilidad por rango de fechas
- Tipos de habitación: Sencilla, Doble, Suite, Presidencial

### 3. Check-in / Check-out
- Proceso completo de check-in con registro de documentos y depósitos
- Check-out con registro de pagos, métodos de pago y calificaciones
- Actualización automática de estados de habitaciones
- Historial completo de check-ins y check-outs

### 4. Gestión de Huéspedes
- Registro completo de información de huéspedes
- **Integración con RENIEC**: Autocompletado de datos con DNI
- Historial de reservas por huésped
- Preferencias y notas especiales
- Búsqueda avanzada de huéspedes
- Estadísticas por huésped

### 5. Reportes y Análisis
- **Reporte de Ocupación**: Análisis de ocupación por día con porcentajes
- **Reporte de Ingresos**: Ingresos por períodos, métodos de pago y tipos de habitación
- **Reporte de Huéspedes**: Top clientes, estadísticas y nacionalidades

## Requisitos

- Python 3.8 o superior
- Django 4.2.7
- SQLite (incluido en Python)
- requests (para API RENIEC)
- python-decouple (opcional, para variables de entorno)

## Instalación

1. Clonar o descargar el proyecto

2. Crear un entorno virtual (recomendado):
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. (Opcional) Configurar API RENIEC:
   - Ver `CONFIGURACION_RENIEC.md` para detalles
   - Crear archivo `.env` con `RENIEC_PROVIDER` y `RENIEC_API_KEY` si deseas usar autocompletado

5. Realizar migraciones:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Crear un superusuario (opcional, para acceder al admin):
```bash
python manage.py createsuperuser
```

7. Ejecutar el servidor de desarrollo:
```bash
python manage.py runserver
```

8. Acceder a la aplicación:
- Sistema: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

## Estructura del Proyecto

```
sistema hotel/
├── hotel/                    # Aplicación principal
│   ├── models.py            # Modelos: Habitación, Huésped, Reserva, CheckIn, CheckOut
│   ├── views.py             # Vistas de todas las funcionalidades
│   ├── forms.py             # Formularios para todos los modelos
│   ├── urls.py              # URLs de la aplicación
│   └── admin.py             # Configuración del admin de Django
├── hotel_sistema/           # Configuración del proyecto
│   ├── settings.py          # Configuración (SQLite, apps, etc.)
│   └── urls.py              # URLs principales
├── templates/               # Templates HTML
│   ├── base.html           # Template base
│   └── hotel/              # Templates de la aplicación
├── manage.py
├── requirements.txt
└── README.md
```

## Modelos de Datos

### Habitación
- Número, tipo, estado, capacidad
- Precio por noche, descripción, servicios

### Huésped
- Información personal completa
- Documento de identidad único
- Preferencias y notas

### Reserva
- Relación con huésped y habitación
- Fechas de entrada y salida
- Cálculo automático de precio total
- Estados de reserva

### CheckIn
- Registro de check-in con fecha/hora
- Documentos recibidos, depósito
- Empleado que realizó el check-in

### CheckOut
- Registro de check-out con fecha/hora
- Total pagado, método de pago
- Calificación, daños observados

## Funcionalidades Clave

### Validaciones Automáticas
- Verificación de disponibilidad antes de crear reservas
- Validación de capacidad de habitaciones
- Validación de fechas (entrada < salida)
- Prevención de sobreventa

### Cálculos Automáticos
- Precio total de reservas (noches × precio/noche)
- Número de noches
- Ocupación diaria
- Ingresos totales

### Estados Automáticos
- Actualización de estado de habitaciones según reservas
- Cambio de estado de reservas al hacer check-in/check-out
- Gestión de estados de limpieza y mantenimiento

## Uso del Sistema

### Para Recepcionistas (Flujo Rápido)

1. **Dashboard**: Ver tareas del día al iniciar sesión
2. **Registro Rápido**: 
   - Ir a "Recepción > Registro Rápido"
   - Ingresar DNI (autocompleta desde RENIEC)
   - Seleccionar habitación y fechas
   - Opcional: hacer check-in automático
3. **Check-in Rápido**: 
   - Ver lista de check-ins pendientes
   - Clic en "Check-in" para proceso rápido
4. **Check-out Rápido**: 
   - Ver lista de check-outs del día
   - Cálculo automático de total a pagar
5. **Walk-in**: Para huéspedes sin reserva previa
6. **Búsqueda**: Usar Ctrl+K o barra de búsqueda en header

### Flujo Tradicional

1. **Configurar Habitaciones**: Crear las habitaciones del hotel con sus características
2. **Registrar Huéspedes**: Agregar información de huéspedes (o usar autocompletado RENIEC)
3. **Crear Reservas**: Realizar reservas verificando disponibilidad
4. **Check-in**: Registrar el ingreso de huéspedes
5. **Check-out**: Registrar la salida y pago
6. **Consultar Reportes**: Analizar ocupación, ingresos y estadísticas

## Tecnologías Utilizadas

- **Backend**: Django 4.2.7
- **Base de Datos**: SQLite
- **Frontend**: Bootstrap 5
- **Formularios**: Django Crispy Forms
- **Iconos**: Bootstrap Icons
- **API Externa**: RENIEC (APISPERU/JSON.pe) para autocompletado de datos
- **Cache**: Django LocMemCache para optimizar consultas RENIEC

## Notas

- El sistema está configurado para desarrollo. Para producción, cambiar `DEBUG = False` en `settings.py`
- Cambiar `SECRET_KEY` en producción
- SQLite es adecuado para desarrollo y pequeños hoteles. Para producción, considerar PostgreSQL o MySQL
- El sistema no incluye autenticación de usuarios. Se puede agregar fácilmente con Django Auth

## Licencia

Este proyecto es de código abierto y está disponible para uso educativo y comercial.


