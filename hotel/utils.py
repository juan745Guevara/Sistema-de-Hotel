"""
Utilidades para el sistema hotelero
"""
import requests
import os
from django.conf import settings
from django.core.cache import cache


def consultar_reniec_dni(dni):
    """
    Consulta datos de un DNI usando API de RENIEC o servicios externos.
    
    Soporta múltiples proveedores:
    - APISPERU (apisperu.com)
    - JSON.pe (json.pe)
    - RENIEC oficial (requiere configuración especial)
    
    Args:
        dni (str): Número de DNI (8 dígitos)
        
    Returns:
        dict: Datos del ciudadano o None si hay error
    """
    if not dni or len(dni) != 8 or not dni.isdigit():
        return None
    
    # Intentar obtener de caché primero (evitar consultas repetidas)
    cache_key = f'reniec_dni_{dni}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Configuración del proveedor (puede ser APISPERU, JSON_PE, etc.)
    provider = getattr(settings, 'RENIEC_PROVIDER', 'APISPERU')
    api_key = getattr(settings, 'RENIEC_API_KEY', '')
    
    datos = None
    
    try:
        if provider == 'APISPERU':
            # APISPERU - https://apisperu.com
            url = f'https://apisperu.com/api/dni/{dni}'
            if api_key:
                headers = {'Authorization': f'Bearer {api_key}'}
            else:
                headers = {}
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success', False):
                    datos = {
                        'nombre': data.get('data', {}).get('nombres', ''),
                        'apellidos': data.get('data', {}).get('apellidoPaterno', '') + ' ' + 
                                   data.get('data', {}).get('apellidoMaterno', ''),
                        'apellido_paterno': data.get('data', {}).get('apellidoPaterno', ''),
                        'apellido_materno': data.get('data', {}).get('apellidoMaterno', ''),
                        'direccion': data.get('data', {}).get('direccion', ''),
                    }
        
        elif provider == 'JSON_PE':
            # JSON.pe - https://json.pe
            url = 'https://json.pe/api/dni'
            params = {'dni': dni}
            if api_key:
                params['token'] = api_key
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success', False):
                    datos = {
                        'nombre': data.get('data', {}).get('nombres', ''),
                        'apellidos': data.get('data', {}).get('apellidoPaterno', '') + ' ' + 
                                   data.get('data', {}).get('apellidoMaterno', ''),
                        'apellido_paterno': data.get('data', {}).get('apellidoPaterno', ''),
                        'apellido_materno': data.get('data', {}).get('apellidoMaterno', ''),
                        'direccion': data.get('data', {}).get('direccion', ''),
                    }
        
        # Si se obtuvieron datos, guardar en caché por 24 horas
        if datos:
            cache.set(cache_key, datos, 86400)  # 24 horas
        
    except requests.RequestException:
        # Error de conexión o timeout
        pass
    except Exception:
        # Otro error
        pass
    
    return datos

