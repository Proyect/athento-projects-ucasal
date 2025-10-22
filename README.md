# Sistema de Actas UCASAL

## 🎯 Descripción

Sistema completo de gestión de actas de examen desarrollado en Django con API REST, panel de administración, validaciones robustas y testing automatizado.

## ✨ Características

- **API REST** completa con Django REST Framework
- **Panel de administración** personalizado para gestión de actas
- **Generación de códigos QR** para validación
- **Sistema de OTP** (One-Time Password) para firma digital
- **Integración con blockchain** para registro de documentos
- **Validaciones robustas** de datos y transiciones de estado
- **Manejo de errores** centralizado con logging estructurado
- **Tests automatizados** con cobertura completa
- **Documentación técnica** detallada

## 🚀 Inicio Rápido

### 1. Configuración del Entorno

```bash
# Crear entorno virtual
   python -m venv .venv

# Activar entorno virtual
# Windows:
   .\.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# Instalar dependencias
   pip install -r requirements.txt
   ```

### 2. Configuración de la Base de Datos

```bash
# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

### 3. Levantar el Servidor

```bash
# Servidor de desarrollo
python manage.py runserver 8012
```

### 4. Acceder a la Aplicación

- **API Principal**: http://localhost:8012/
- **Documentación**: http://localhost:8012/docs/
- **Panel Admin**: http://localhost:8012/admin/
- **Gestión de Actas**: http://localhost:8012/admin/actas/acta/

## 📋 Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información de la API |
| GET | `/docs/` | Documentación completa |
| POST | `/actas/qr/` | Generar código QR |
| POST | `/actas/getconfig/` | Obtener configuración |
| POST | `/actas/{uuid}/registerotp/` | Registrar OTP |
| POST | `/actas/{uuid}/sendotp/` | Enviar código OTP |
| POST | `/actas/{uuid}/bfaresponse/` | Respuesta blockchain |
| POST | `/actas/{uuid}/reject/` | Rechazar acta |

## 🧪 Testing

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

- **`test_models.py`**: Tests del modelo Acta (validaciones, métodos, estados)
- **`test_endpoints.py`**: Tests de endpoints API (casos exitosos y errores)
- **`test_admin.py`**: Tests del panel de administración (CRUD, acciones masivas)

## 🔧 Configuración

### Variables de Entorno

Copia `env.example` a `.env` y configura:

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Base de datos
DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=ucasal/db.sqlite3

# Servicios UCASAL
UCASAL_TOKEN_SVC_URL=https://api.ucasal.edu.ar/token
UCASAL_QR_SVC_URL=https://api.ucasal.edu.ar/qr
UCASAL_STAMPS_SVC_URL=https://api.ucasal.edu.ar/stamps
```

## 📊 Modelo de Datos

### Acta

Modelo principal para gestionar actas de examen con:

- **Identificación**: UUID único, título, descripción
- **Docente**: Email, nombre, código de sector
- **Control de versiones**: Número de revisión, UUID de acta previa
- **Estados**: Recibida, Pendiente OTP, Firmada, Rechazada, etc.
- **Firma digital**: OTP, coordenadas GPS, IP, user agent
- **Blockchain**: Hash del documento, estado de registro
- **Auditoría**: Fechas de creación, modificación, firma

### Estados Válidos

1. **`recibida`** → `pendiente_otp` | `rechazada`
2. **`pendiente_otp`** → `firmada` | `rechazada`
3. **`firmada`** → `pendiente_blockchain`
4. **`pendiente_blockchain`** → `firmada` | `fallo_blockchain`
5. **`fallo_blockchain`** → `pendiente_otp`
6. **`rechazada`** → `pendiente_otp` (reactivación)

## 🛡️ Validaciones

### Modelo
- **Email**: Formato válido
- **Nombre**: Solo letras, espacios y puntos
- **Código sector**: Exactamente 3 dígitos
- **Coordenadas**: Latitud (-90 a 90), Longitud (-180 a 180)
- **Transiciones**: Estados válidos según reglas de negocio

### Endpoints
- **OTP**: 6 dígitos numéricos
- **IP**: Formato IPv4 válido
- **GPS**: Precisión en formato "Xm"
- **UUID**: Formato UUID válido

## 🔍 Manejo de Errores

### Códigos de Error
- `ACTA_NOT_FOUND`: Acta no encontrada
- `VALIDATION_ERROR`: Error de validación
- `UCASAL_SERVICE_ERROR`: Error en servicio UCASAL
- `INTEGRITY_ERROR`: Error de integridad de datos

### Middleware
- **ErrorHandlingMiddleware**: Manejo global de excepciones
- **RequestLoggingMiddleware**: Logging de requests/responses
- **SecurityHeadersMiddleware**: Headers de seguridad

## 📚 Documentación

- **API**: http://localhost:8012/docs/
- **Técnica**: `docs/API_DOCUMENTATION.md`
- **Admin**: Panel web en `/admin/`

## 🐳 Docker

```bash
# Construir y levantar
docker-compose build
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

## 🔧 Desarrollo

### Estructura del Proyecto

```
├── core/                    # Configuración base
│   ├── exceptions.py       # Excepciones personalizadas
│   └── middleware.py       # Middleware personalizado
├── endpoints/actas/        # App principal
│   ├── models.py          # Modelo Acta
│   ├── admin.py           # Admin personalizado
│   ├── views.py           # Vistas básicas
│   ├── actas.py           # Endpoints API
│   ├── validators.py      # Validadores personalizados
│   └── tests/             # Tests automatizados
├── external_services/     # Servicios externos
├── operations/            # Operaciones de negocio
├── management/commands/   # Comandos Django
├── mail_templates/        # Templates de email
└── docs/                  # Documentación
```

### Agregar Nuevas Funcionalidades

1. **Modelos**: Agregar en `endpoints/actas/models.py`
2. **Endpoints**: Agregar en `endpoints/actas/actas.py`
3. **Validaciones**: Agregar en `endpoints/actas/validators.py`
4. **Tests**: Agregar en `endpoints/actas/tests/`
5. **Admin**: Registrar en `endpoints/actas/admin.py`

## 📈 Monitoreo

- **Logs**: Estructurados en formato JSON
- **Métricas**: Requests, errores, tiempo de respuesta
- **Alertas**: Errores críticos, servicios caídos

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## 📞 Contacto

- **Email**: arieldiaz.sistemas@gmail.com
- **Documentación**: `/docs/`
- **Issues**: GitHub Issues

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.
