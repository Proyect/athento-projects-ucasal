# UCASAL – Sistema de Actas y Títulos

Proyecto Django que expone APIs y UI para gestionar **actas de examen** y **títulos** integrados con Athento y servicios externos UCASAL.

## 1. Requisitos

- Python 3.10+ (recomendado 3.11)
- pip / venv
- (Opcional) Docker y docker-compose para Prometheus/Grafana
- Base de datos: por defecto SQLite; en producción se usa PostgreSQL

## 2. Instalación y configuración

```bash
# Clonar el repositorio
git clone <URL_DEL_REPO>
cd athento-projects-ucasal

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2.1 Variables de entorno

Crea un archivo `.env` en la raíz (ya está ignorado por Git). Ejemplo mínimo para entorno local:

```env
DJANGO_SECRET_KEY=dev-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Base de datos local (SQLite por defecto)
DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=ucasal/db.sqlite3

# Media
MEDIA_ROOT=media
MEDIA_TMP=tmp

# API Athento (para ambiente real)
API_BASE_URL=https://ucasal-uat.athento.com
API_ADMIN_USERNAME=usuario@ucasal.edu.ar
API_ADMIN_PASSWORD=***

# Servicios UCASAL (token, qr, acortar URL, etc.)
UCASAL_TOKEN_SVC_URL=...
UCASAL_TOKEN_SVC_USER=...
UCASAL_TOKEN_SVC_PASSWORD=...
UCASAL_SHORTEN_URL_SVC_URL=...
UCASAL_SHORTEN_URL_SVC_ENV=desarrollo
UCASAL_ACTA_VALIDATION_URL_TEMPLATE=https://.../validar/{uuid}
UCASAL_OTP_VALIDATION_URL_TEMPLATE=https://.../otp/validate?usuario={usuario}&token={token}

# Validación de títulos
UCASAL_TITULO_VALIDATION_URL_TEMPLATE=https://www.ucasal.edu.ar/validar/index.php?d=titulo&e=testing&uuid={uuid}

# Modo mocks (para desarrollo sin servicios externos)
UCASAL_USE_MOCKS=true
```

> **Importante:** Nunca subas credenciales reales al repositorio. Mantén `.env` fuera de Git (ya está en `.gitignore`).

## 3. Puesta en marcha

Aplicar migraciones y levantar el servidor de desarrollo:

```bash
python manage.py migrate
python manage.py createsuperuser  # si aún no tienes usuario admin
python manage.py runserver 8012
```

La aplicación estará disponible en:

- API base: <http://localhost:8012/>
- Admin Django: <http://localhost:8012/admin/>
- UI de títulos: <http://localhost:8012/ui/>

## 4. Endpoints principales

### 4.1 Actas

- `GET /` – Información general de la API.
- `POST /actas/qr/` – Generar código QR.
- `POST /actas/getconfig/` – Obtener configuración.
- `POST /actas/{uuid}/sendotp/` – Enviar OTP.
- `POST /actas/{uuid}/registerotp/` – Registrar OTP y firmar acta.
- `POST /actas/{uuid}/bfaresponse/` – Callback blockchain (actas).
- `POST /actas/{uuid}/reject/` – Rechazar acta.

### 4.2 Títulos (API REST)

- `GET /api/titulos/` – Listar títulos (consulta Athento).
- `POST /api/titulos/` – Crear título vía API (file_base64).
- `GET /api/titulos/{uuid}/` – Detalle de título.
- `PUT /api/titulos/{uuid}/` – Actualizar metadatos / archivo.
- `DELETE /api/titulos/{uuid}/` – Eliminar.
- `GET /api/titulos/{uuid}/download/` – URL de descarga.
- `POST /api/titulos/{uuid}/estado/` – Informar estado a UCASAL.
- `POST /api/titulos/{uuid}/validar-otp/` – Validar OTP del título.
- `POST /api/titulos/{uuid}/firmar/` – Firma digital del título.

La mayoría de estos endpoints usan **JWT** (SimpleJWT). El login suele estar expuesto en `/api/auth/login/` (ver `endpoints/auth/`).

### 4.3 UI de Títulos

Rutas principales (todas requieren usuario en grupo `Titulos`):

- `/ui/` – Redirección a listado de títulos.
- `/ui/titulos/` – Listado con búsqueda (DataTables) contra Athento.
- `/ui/titulos/nuevo/` – Subir nuevo título (PDF + metadatos).
- `/ui/titulos/{uuid}/` – Detalle del título.
- `/ui/titulos/{uuid}/edit/` – Editar metadatos (JSON).
- `/ui/titulos/{uuid}/replace/` – Reemplazar archivo PDF.
- `/ui/titulos/{uuid}/attach/` – Adjuntar documentos relacionados.
- `/ui/titulos/{uuid}/firm/` – Marcar como firmado (ciclo de vida).
- `/ui/titulos/{uuid}/reject/` – Marcar como rechazado.
- `/ui/titulos/{uuid}/state/` – Cambiar estado manualmente respetando el ciclo de vida.
- `/ui/titulos/{uuid}/status/` – Ver estado/datos crudos del documento.

## 5. Ciclo de vida de Títulos

El ciclo de vida de títulos está centralizado en `ucasal/utils.py` mediante:

- `TituloStates`: constantes de estado (Recibido, Pendiente Aprobación UA, Aprobado UA, Pendiente Aprobación R, Aprobado R, Pendiente Firma SG, Firmado SG, Título Emitido, Rechazado).
- `TITULO_TRANSITIONS_ALLOWED`: matriz de transiciones permitidas.
- `can_transition(from_state, to_state)`: helper para validar transiciones.

Se aplica en:

- **API** (`endpoints/titulos/titulos.py`):
  - `informar_estado` valida `can_transition` y actualiza estado en Athento + UCASAL.
  - `firmar_titulo` exige que el estado sea `Pendiente Firma SG`.

- **UI** (`ucasal/views_ui.py`):
  - `firm_title_view`, `reject_title_view`, `change_title_state_view` leen el estado actual desde Athento y sólo permiten transiciones válidas.

De esta forma, ni la API ni la UI pueden saltarse pasos del workflow.

## 6. Modo mocks vs. entorno real

### 6.1 Modo mocks (desarrollo)

Con `UCASAL_USE_MOCKS=true`:

- `get_auth_token` devuelve un token estático.
- `get_short_url` genera URLs cortas falsas.
- `notify_titulo_estado` simula respuesta exitosa.
- `validate_otp` acepta sólo OTP `123456`.
- Algunos callbacks como `/titulos/{uuid}/bfaresponse/` emulan comportamientos para tests.

Útil para trabajar sin depender de los servicios reales de UCASAL/Athento.

### 6.2 Entorno real (UAT / Producción)

Con `UCASAL_USE_MOCKS=false`:

- Todas las llamadas a UCASAL/Athento son reales.
- Debes configurar correctamente:
  - `API_BASE_URL`, `API_ADMIN_USERNAME`, `API_ADMIN_PASSWORD`.
  - `UCASAL_*_SVC_URL` para token/QR/shorten/etc.

## 7. Panel de administración (MEJORAS_ADMIN)

Principales entradas del admin mejoradas (ver `MEJORAS_ADMIN.md`):

- **Actas**: `/admin/actas/acta/`
- **Títulos (modelo local de prueba)**: `/admin/model/titulofile/`
- **Archivos (Files)**: `/admin/model/file/`
- **Tipos de Documento (Doctypes)**: `/admin/model/doctype/`
- **Estados de Ciclo de Vida (LifeCycleState)**: `/admin/model/lifecyclestate/`

Ofrecen filtros, acciones masivas y visualización de metadata/features.

## 8. Métricas y monitoreo

El proyecto incluye integración con Prometheus y Grafana (ver `MONITOREO_PROMETHEUS_GRAFANA.md` y `prometheus.yml`):

- Endpoint de métricas Prometheus: `/metrics`.
- Métricas de:
  - Endpoints de actas y títulos.
  - Servicios externos UCASAL (latencias, errores).
  - Estados emitidos, tiempos de emisión, etc.

## 9. Tests

Para ejecutar los tests de títulos (script de pruebas de endpoints):

```bash
python test_titulos_api.py
```

Notas:

- En modo real, muchas pruebas requieren acceso a `https://ucasal-uat.athento.com` y servicios UCASAL.
- En desarrollo, se recomienda `UCASAL_USE_MOCKS=true` para evitar timeouts si UAT no está disponible.

También puedes usar los tests estándar de Django si existen módulos de tests:

```bash
python manage.py test
```

## 10. Git y carpetas ignoradas

En `.gitignore` se ignoran, entre otros:

- Archivos `.env`, `.aux`, binarios, media, etc.
- Carpeta `otros/` donde se guarda código auxiliar/clonado que no debe versionarse.

Asegúrate de no añadir manualmente estos archivos con `git add` para mantener el repositorio limpio.
