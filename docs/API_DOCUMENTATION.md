# Documentación de la API UCASAL - Sistema de Actas

## Tabla de Contenidos
1. [Introducción](#introducción)
2. [Configuración](#configuración)
3. [Endpoints](#endpoints)
4. [Modelos](#modelos)
5. [Validaciones](#validaciones)
6. [Manejo de Errores](#manejo-de-errores)
7. [Testing](#testing)
8. [Despliegue](#despliegue)

## Introducción

El Sistema de Actas UCASAL es una API REST desarrollada en Django que permite la gestión completa del ciclo de vida de actas de examen, incluyendo:

- Generación de códigos QR
- Validación de OTP (One-Time Password)
- Firma digital de documentos
- Integración con servicios de blockchain
- Panel de administración web

### Características Principales

- **API REST** con Django REST Framework
- **Validaciones robustas** de datos
- **Manejo de errores** centralizado
- **Tests automatizados** con cobertura completa
- **Documentación interactiva** en `/docs/`
- **Panel de administración** personalizado
- **Logging estructurado** para monitoreo

## Configuración

### Variables de Entorno

```bash
# Django Configuration
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=ucasal/db.sqlite3

# Media Configuration
MEDIA_ROOT=media
MEDIA_TMP=tmp

# UCASAL Services
UCASAL_TOKEN_SVC_URL=https://api.ucasal.edu.ar/token
UCASAL_QR_SVC_URL=https://api.ucasal.edu.ar/qr
UCASAL_STAMPS_SVC_URL=https://api.ucasal.edu.ar/stamps
UCASAL_CHANGE_ACTA_SVC_URL=https://api.ucasal.edu.ar/change-acta
UCASAL_SHORTEN_URL_SVC_URL=https://api.ucasal.edu.ar/shorten
UCASAL_OTP_VALIDITY_SECONDS=300
```

### Instalación

```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.\.venv\Scripts\Activate.ps1  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Levantar servidor
python manage.py runserver
```

## Endpoints

### Información General

- **Base URL**: `http://localhost:8012`
- **Formato**: JSON
- **Autenticación**: Bearer Token (algunos endpoints)

### Endpoints Disponibles

#### 1. Información de la API

**GET** `/`

```json
{
  "message": "UCASAL API - Sistema de Actas",
  "version": "1.0.0",
  "endpoints": {
    "admin": "/admin/",
    "actas": "/actas/",
    "qr": "/actas/qr/",
    "getconfig": "/actas/getconfig/",
    "docs": "/docs/"
  }
}
```

#### 2. Documentación

**GET** `/docs/`

Retorna documentación completa de la API en formato JSON.

#### 3. Generar Código QR

**POST** `/actas/qr/`

**Body:**
```json
{
  "url": "https://example.com"
}
```

**Response:** Imagen PNG del código QR

#### 4. Obtener Configuración

**POST** `/actas/getconfig/`

**Body:**
```json
{
  "key": "config_key",
  "is_secret": false
}
```

**Response:**
```
valor_de_configuracion
```

#### 5. Registrar OTP

**POST** `/actas/{uuid}/registerotp/`

**Body:**
```json
{
  "otp": "123456",
  "ip": "192.168.1.1",
  "latitude": -34.6037,
  "longitude": -58.3816,
  "accuracy": "10m",
  "user_agent": "Mozilla/5.0..."
}
```

**Response:**
```json
{
  "otp_is_valid": true,
  "callback_url": "https://api.ucasal.edu.ar/bfaresponse"
}
```

#### 6. Enviar OTP

**POST** `/actas/{uuid}/sendotp/`

**Response:**
```json
{
  "sent_to": "profesor@ucasal.edu.ar",
  "expiration": 9999999999
}
```

#### 7. Respuesta Blockchain

**POST** `/actas/{uuid}/bfaresponse/`

**Body:**
```json
{
  "status": "success"
}
```

**Response:**
```
Resultado BFA guardado exitosamente
```

#### 8. Rechazar Acta

**POST** `/actas/{uuid}/reject/`

**Body:**
```json
{
  "motivo": "Error en los datos del estudiante"
}
```

**Response:**
```
Acta rechazada exitosamente
```

## Modelos

### Acta

Modelo principal para gestionar actas de examen.

#### Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `uuid` | UUIDField | Identificador único (PK) |
| `titulo` | CharField(200) | Título del acta |
| `descripcion` | TextField | Descripción opcional |
| `docente_asignado` | EmailField | Email del docente |
| `nombre_docente` | CharField(100) | Nombre del docente |
| `codigo_sector` | CharField(10) | Código de sector (3 dígitos) |
| `numero_revision` | IntegerField | Número de revisión |
| `uuid_acta_previa` | UUIDField | UUID de acta previa |
| `estado` | CharField(20) | Estado actual |
| `fecha_creacion` | DateTimeField | Fecha de creación |
| `fecha_firma` | DateField | Fecha de firma |
| `fecha_rechazo` | DateField | Fecha de rechazo |
| `motivo_rechazo` | TextField | Motivo de rechazo |
| `firmada_con_otp` | BooleanField | Si fue firmada con OTP |
| `registro_blockchain` | CharField(20) | Estado en blockchain |
| `hash_documento` | CharField(64) | Hash del documento |
| `ip_firma` | GenericIPAddressField | IP de firma |
| `latitud` | FloatField | Latitud GPS |
| `longitud` | FloatField | Longitud GPS |
| `precision_gps` | CharField(50) | Precisión GPS |
| `user_agent` | TextField | User agent |
| `activa` | BooleanField | Si está activa |
| `fecha_modificacion` | DateTimeField | Fecha de modificación |

#### Estados Válidos

- `recibida`: Acta recibida
- `pendiente_otp`: Pendiente de firma OTP
- `pendiente_blockchain`: Pendiente de registro en blockchain
- `firmada`: Firmada completamente
- `fallo_blockchain`: Fallo en blockchain
- `rechazada`: Rechazada

#### Métodos

- `es_revision()`: Indica si es una revisión
- `puede_firmar()`: Indica si puede ser firmada
- `puede_rechazar()`: Indica si puede ser rechazada
- `get_estado_display_color()`: Color CSS del estado

## Validaciones

### Validaciones de Modelo

1. **Email del docente**: Formato válido
2. **Nombre del docente**: Solo letras, espacios y puntos
3. **Código de sector**: Exactamente 3 dígitos
4. **Coordenadas GPS**: Latitud (-90 a 90), Longitud (-180 a 180)
5. **Acta de revisión**: Debe tener UUID de acta previa
6. **Estados**: Transiciones válidas entre estados
7. **Fechas**: No puede estar firmada y rechazada simultáneamente

### Validaciones de Endpoints

1. **OTP**: 6 dígitos numéricos
2. **IP**: Formato IPv4 válido
3. **User Agent**: Longitud entre 10 y 500 caracteres
4. **Precisión GPS**: Formato "Xm" (ej: "10m")
5. **Motivo de rechazo**: Mínimo 10 caracteres
6. **UUID**: Formato UUID válido

## Manejo de Errores

### Códigos de Error

| Código | Descripción |
|--------|-------------|
| `ACTA_NOT_FOUND` | Acta no encontrada |
| `UCASAL_SERVICE_ERROR` | Error en servicio UCASAL |
| `VALIDATION_ERROR` | Error de validación |
| `INTEGRITY_ERROR` | Error de integridad de datos |
| `ATHENTOSE_ERROR` | Error del sistema |
| `INTERNAL_SERVER_ERROR` | Error interno del servidor |

### Formato de Error

```json
{
  "error": "Tipo de error",
  "message": "Descripción del error",
  "code": "CODIGO_ERROR",
  "field": "campo_especifico"  // Solo para errores de validación
}
```

### Middleware de Errores

- **ErrorHandlingMiddleware**: Manejo global de excepciones
- **RequestLoggingMiddleware**: Logging de requests/responses
- **SecurityHeadersMiddleware**: Headers de seguridad

## Testing

### Ejecutar Tests

```bash
# Todos los tests
python manage.py test

# Tests específicos
python manage.py test endpoints.actas.tests.test_models
python manage.py test endpoints.actas.tests.test_endpoints
python manage.py test endpoints.actas.tests.test_admin

# Con cobertura
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Estructura de Tests

- `test_models.py`: Tests del modelo Acta
- `test_endpoints.py`: Tests de endpoints API
- `test_admin.py`: Tests del panel de administración

### Cobertura de Tests

- **Modelos**: 100% de métodos y validaciones
- **Endpoints**: 100% de rutas y casos de error
- **Admin**: 100% de funcionalidades del panel

## Despliegue

### Desarrollo

```bash
python manage.py runserver 8012
```

### Producción

```bash
# Con Gunicorn
gunicorn ucasal.wsgi:application --bind 0.0.0.0:8012

# Con Docker
docker-compose up -d
```

### Variables de Entorno de Producción

```bash
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=your-production-secret-key
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=ucasal_prod
DATABASE_USER=ucasal_user
DATABASE_PASSWORD=your-db-password
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

### Monitoreo

- **Logs**: Estructurados en formato JSON
- **Métricas**: Requests, errores, tiempo de respuesta
- **Alertas**: Errores críticos, servicios caídos

## Contacto

- **Email**: arieldiaz.sistemas@gmail.com
- **Documentación**: `/docs/`
- **Admin**: `/admin/`


