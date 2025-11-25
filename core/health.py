"""
Health check endpoint para monitoreo del sistema
"""
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
from django.db import connection
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Endpoint de health check para monitoreo.
    GET /health/
    
    Verifica:
    - Estado de la aplicación
    - Conexión a base de datos
    - Conexión a Redis (si está configurado)
    """
    health_status = {
        'status': 'healthy',
        'checks': {}
    }
    
    overall_healthy = True
    
    # Check 1: Base de datos
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status['checks']['database'] = {
            'status': 'healthy',
            'message': 'Database connection OK'
        }
    except Exception as e:
        overall_healthy = False
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }
        logger.error(f'Health check - Database failed: {e}')
    
    # Check 2: Redis/Cache
    try:
        cache.set('health_check', 'ok', 10)
        cache_result = cache.get('health_check')
        if cache_result == 'ok':
            health_status['checks']['cache'] = {
                'status': 'healthy',
                'message': 'Cache connection OK'
            }
        else:
            overall_healthy = False
            health_status['checks']['cache'] = {
                'status': 'unhealthy',
                'message': 'Cache test failed'
            }
    except Exception as e:
        # Redis no es crítico, solo advertir
        health_status['checks']['cache'] = {
            'status': 'degraded',
            'message': f'Cache not available: {str(e)}'
        }
        logger.warning(f'Health check - Cache unavailable: {e}')
    
    # Check 3: Configuración básica
    try:
        if not settings.SECRET_KEY or settings.SECRET_KEY == 'dev-secret-key-change-in-production':
            health_status['checks']['configuration'] = {
                'status': 'warning',
                'message': 'Using default SECRET_KEY (not recommended for production)'
            }
        else:
            health_status['checks']['configuration'] = {
                'status': 'healthy',
                'message': 'Configuration OK'
            }
    except Exception as e:
        health_status['checks']['configuration'] = {
            'status': 'warning',
            'message': f'Configuration check failed: {str(e)}'
        }
    
    # Determinar status general
    if overall_healthy:
        health_status['status'] = 'healthy'
        status_code = 200
    else:
        health_status['status'] = 'unhealthy'
        status_code = 503
    
    return JsonResponse(health_status, status=status_code)



