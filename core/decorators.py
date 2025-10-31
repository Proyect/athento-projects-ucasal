"""
Decoradores personalizados para rate limiting y autenticación
"""
from functools import wraps
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited


def rate_limit_decorator(key='ip', rate='10/m', method='POST'):
    """
    Decorador para aplicar rate limiting
    
    Args:
        key: Clave para identificar el límite ('ip', 'user', etc.)
        rate: Tasa permitida (ej: '10/m' = 10 por minuto)
        method: Método HTTP al que aplicar
    """
    def decorator(func):
        @wraps(func)
        @ratelimit(key=key, rate=rate, method=method)
        def wrapper(request, *args, **kwargs):
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def handle_rate_limit_exception(func):
    """
    Maneja excepciones de rate limiting y devuelve respuesta JSON apropiada
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Ratelimited:
            return JsonResponse(
                {
                    'error': 'Rate limit excedido',
                    'message': 'Has excedido el límite de solicitudes. Por favor intenta más tarde.',
                    'code': 'RATE_LIMIT_EXCEEDED'
                },
                status=429
            )
    return wrapper

