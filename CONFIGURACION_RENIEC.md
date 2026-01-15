# Configuración de API RENIEC

El sistema incluye integración con APIs de RENIEC para autocompletar datos de huéspedes usando su DNI.

## Proveedores Soportados

### 1. APISPERU (Recomendado)
- URL: https://apisperu.com
- Requiere API Key (opcional para pruebas)
- Más fácil de configurar

### 2. JSON.pe
- URL: https://json.pe
- Requiere token de API
- Alternativa a APISPERU

## Configuración

### Opción 1: Variables de Entorno (Recomendado)

Crear un archivo `.env` en la raíz del proyecto:

```env
RENIEC_PROVIDER=APISPERU
RENIEC_API_KEY=tu_api_key_aqui
```

### Opción 2: Configuración Directa

Editar `hotel_sistema/settings.py`:

```python
RENIEC_PROVIDER = 'APISPERU'  # o 'JSON_PE'
RENIEC_API_KEY = 'tu_api_key_aqui'
```

## Obtener API Key

### APISPERU
1. Visitar https://apisperu.com
2. Registrarse y obtener API Key
3. Algunos planes son gratuitos para pruebas

### JSON.pe
1. Visitar https://json.pe
2. Registrarse y obtener token
3. Configurar en settings

## Uso

El autocompletado funciona automáticamente en:
- **Registro Rápido**: Al ingresar DNI y presionar Tab
- **Walk-in**: Al ingresar DNI y presionar Tab

El sistema:
1. Primero busca en la base de datos local
2. Si no existe, consulta la API de RENIEC
3. Autocompleta nombre, apellidos y otros datos disponibles

## Notas

- Los datos se cachean por 24 horas para evitar consultas repetidas
- Si no hay API Key, el sistema intentará consultar sin autenticación (puede tener límites)
- El sistema funciona sin API Key, pero el autocompletado desde RENIEC no estará disponible

