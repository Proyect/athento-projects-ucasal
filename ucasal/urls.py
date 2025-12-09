from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.shortcuts import redirect
from endpoints.actas.actas import routes as actas_routes
from endpoints.titulos.titulos import routes as titulos_routes
from endpoints.titulos.titulos import informar_estado, validar_otp, firmar_titulo
from endpoints.titulos.api_views import titles_collection, title_detail, title_download
from core.health import health_check
from ucasal.views_ui import (
    login_view,
    logout_view,
    titles_list_view,
    upload_title_view,
    title_detail_view,
    delete_title_view,
    titles_console_view,
    titles_search_api,
    titles_bulk_delete_api,
)
from ucasal.views_api import titulos_command

app_name = 'ucasal'

def home_view(request):
    return JsonResponse({
        'message': 'UCASAL API - Sistema de Actas y Títulos',
        'version': '1.0.0',
        'endpoints': {
            'admin': '/admin/',
            'actas': '/actas/',
            'titulos': '/titulos/',
            'qr': '/actas/qr/',
            'getconfig': '/actas/getconfig/',
            'docs': '/docs/'
        }
    })

def docs_view(request):
    return JsonResponse({
        'title': 'UCASAL API Documentation',
        'version': '1.0.0',
        'description': 'API para el sistema de gestión de actas de UCASAL',
        'endpoints': {
            'GET /': {
                'description': 'Información general de la API',
                'response': 'JSON con información de la API'
            },
            'GET /admin/': {
                'description': 'Panel de administración de Django',
                'authentication': 'Requiere login de admin'
            },
            'POST /actas/qr/': {
                'description': 'Generar código QR',
                'body': {'url': 'string'},
                'response': 'Imagen PNG del QR'
            },
            'POST /actas/getconfig/': {
                'description': 'Obtener configuración',
                'body': {'key': 'string', 'is_secret': 'boolean'},
                'response': 'Valor de configuración'
            },
            'POST /actas/{uuid}/registerotp/': {
                'description': 'Registrar OTP para acta',
                'body': {'otp': 'int', 'ip': 'string', 'latitude': 'float', 'longitude': 'float', 'accuracy': 'string', 'user_agent': 'string'},
                'response': 'JSON con resultado'
            },
            'POST /actas/{uuid}/sendotp/': {
                'description': 'Enviar código OTP',
                'response': 'JSON con información de envío'
            },
            'POST /actas/{uuid}/bfaresponse/': {
                'description': 'Respuesta de blockchain',
                'body': {'status': 'success|failure'},
                'response': 'JSON con resultado'
            },
            'POST /actas/{uuid}/reject/': {
                'description': 'Rechazar acta',
                'body': {'motivo': 'string'},
                'response': 'JSON con resultado'
            }
        },
        'authentication': {
            'type': 'Bearer Token',
            'note': 'Algunos endpoints requieren autenticación'
        },
        'base_url': 'http://localhost:8012',
        'contact': {
            'email': 'arieldiaz.sistemas@gmail.com'
        }
    })

def ui_root(request):
    if request.user.is_authenticated:
        return redirect('ui_titles_list')
    else:
        return redirect('ui_login')

urlpatterns = [
    path('', home_view, name='home'),
    path('docs/', docs_view, name='docs'),
    path('docs', docs_view),
    path('health/', health_check, name='health'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('endpoints.auth.urls')),
    # Nueva API REST para títulos
    path('api/titulos/', titles_collection, name='api_titulos_collection'),
    path('api/titulos/<uuid:uuid>/', title_detail, name='api_titulos_detail'),
    path('api/titulos/<uuid:uuid>/download/', title_download, name='api_titulos_download'),
    path('api/titulos/<uuid:uuid>/estado/', informar_estado, name='api_titulos_estado'),
    path('api/titulos/<uuid:uuid>/validar-otp/', validar_otp, name='api_titulos_validar_otp'),
    path('api/titulos/<uuid:uuid>/firmar/', firmar_titulo, name='api_titulos_firmar'),
    path('api/titulos/command', titulos_command, name='api_titulos_command'),
    path('athento/', include('endpoints.files.urls')),
    path('actas/', include('endpoints.actas.urls')),
    # UI simple para gestionar títulos
    path('ui/', ui_root, name='ui_root'),
    path('ui', ui_root),
    path('ui/login/', login_view, name='ui_login'),
    path('ui/logout/', logout_view, name='ui_logout'),
    path('ui/titulos/', titles_list_view, name='ui_titles_list'),
    path('ui/titulos/console/', titles_console_view, name='ui_titles_console'),
    path('ui/api/titulos/', titles_search_api, name='ui_titles_search_api'),
    path('ui/api/titulos/bulk-delete/', titles_bulk_delete_api, name='ui_titles_bulk_delete_api'),
    path('ui/titulos/nuevo/', upload_title_view, name='ui_upload_title'),
    path('ui/titulos/<uuid:uuid>/', title_detail_view, name='ui_title_detail'),
    path('ui/titulos/<uuid:uuid>/delete/', delete_title_view, name='ui_title_delete'),
    # Prometheus metrics endpoint
    path('', include('django_prometheus.urls')),
    # Incluir las rutas definidas en actas.py y titulos.py
] + actas_routes + titulos_routes

# Servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    # Servir estáticos descubiertos por los finders (incluye admin y app static)
    urlpatterns += staticfiles_urlpatterns()
    # Servir también desde STATIC_ROOT (tras collectstatic)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Servir media desde MEDIA_ROOT
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)