from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from endpoints.actas.actas import routes as actas_routes
from endpoints.titulos.titulos import routes as titulos_routes

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

urlpatterns = [
    path('', home_view, name='home'),
    path('docs/', docs_view, name='docs'),
    path('admin/', admin.site.urls),
    path('actas/', include('endpoints.actas.urls')),
    # Incluir las rutas definidas en actas.py y titulos.py
] + actas_routes + titulos_routes

# Servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)