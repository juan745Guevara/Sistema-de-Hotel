"""Contexto global de plantillas."""


def moneda(request):
    """Moneda del sistema (Perú — soles)."""
    return {
        'MONEDA_SIMBOLO': 'S/',
        'MONEDA_CODIGO': 'PEN',
        'MONEDA_NOMBRE': 'soles',
    }
