"""
Middleware personalizado para manejo de errores
"""
import logging
import traceback
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from .exceptions import AthentoseError, UCASALServiceError, ActaNotFoundError

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware para manejo global de errores
    """
    
    def process_exception(self, request, exception):
        """Procesa excepciones no manejadas"""
        
        # Log del error
        logger.error(
            f"Error no manejado: {type(exception).__name__}: {str(exception)}",
            extra={
                'request_path': request.path,
                'request_method': request.method,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'traceback': traceback.format_exc()
            }
        )
        
        # Manejo específico por tipo de excepción
        if isinstance(exception, ActaNotFoundError):
            return JsonResponse({
                'error': 'Acta no encontrada',
                'message': str(exception),
                'code': 'ACTA_NOT_FOUND'
            }, status=404)
        
        elif isinstance(exception, UCASALServiceError):
            return JsonResponse({
                'error': 'Error en servicio UCASAL',
                'message': str(exception),
                'code': 'UCASAL_SERVICE_ERROR'
            }, status=503)
        
        elif isinstance(exception, ValidationError):
            return JsonResponse({
                'error': 'Error de validación',
                'message': str(exception),
                'code': 'VALIDATION_ERROR',
                'field': getattr(exception, 'field', None)
            }, status=400)
        
        elif isinstance(exception, IntegrityError):
            return JsonResponse({
                'error': 'Error de integridad de datos',
                'message': 'Los datos proporcionados violan las reglas de integridad',
                'code': 'INTEGRITY_ERROR'
            }, status=400)
        
        elif isinstance(exception, AthentoseError):
            return JsonResponse({
                'error': 'Error del sistema',
                'message': str(exception),
                'code': 'ATHENTOSE_ERROR'
            }, status=500)
        
        # Error genérico
        return JsonResponse({
            'error': 'Error interno del servidor',
            'message': 'Ha ocurrido un error inesperado',
            'code': 'INTERNAL_SERVER_ERROR'
        }, status=500)

class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware para logging de requests
    """
    
    def process_request(self, request):
        """Log de request entrante"""
        logger.info(
            f"Request: {request.method} {request.path}",
            extra={
                'request_path': request.path,
                'request_method': request.method,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'remote_addr': request.META.get('REMOTE_ADDR', ''),
                'content_type': request.META.get('CONTENT_TYPE', '')
            }
        )
    
    def process_response(self, request, response):
        """Log de response saliente"""
        logger.info(
            f"Response: {request.method} {request.path} - {response.status_code}",
            extra={
                'request_path': request.path,
                'request_method': request.method,
                'status_code': response.status_code,
                'content_type': response.get('Content-Type', '')
            }
        )
        return response

class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware para headers de seguridad
    """
    
    def process_response(self, request, response):
        """Agrega headers de seguridad"""
        from django.conf import settings

        # No aplicar headers estrictos a archivos estáticos o media (evita bloquear fuentes e imágenes)
        static_url = getattr(settings, 'STATIC_URL', '/static/')
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        if request.path.startswith(static_url) or request.path.startswith(media_url):
            return response

        # Headers de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        
        # CSP básico (prioriza estáticos locales y habilita los CDNs usados)
        csp = [
            "default-src 'self'",
            # Permitir JS local y desde CDNs específicos (jQuery/DataTables)
            "script-src 'self' 'unsafe-inline' https://code.jquery.com https://cdn.datatables.net",
            "script-src-elem 'self' 'unsafe-inline' https://code.jquery.com https://cdn.datatables.net",
            # Permitir CSS local y desde CDN de DataTables
            "style-src 'self' 'unsafe-inline' https://cdn.datatables.net",
            "style-src-elem 'self' 'unsafe-inline' https://cdn.datatables.net",
            # Imágenes locales y data URIs
            "img-src 'self' data:",
            # Permitir fuentes locales y data/blob
            "font-src 'self' data: blob:",
            # Conexiones XHR/fetch (solo mismo origen)
            "connect-src 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp)
        
        return response




