## Testing automático

Se han creado mocks automáticos para los paquetes internos (`sp_logger`, `sp_athento_config`, `sp_totp_generator`, `sp_form_totp_notifier`, `sp_pdf_otp_simple_signer`). Esto permite levantar la app y ejecutar pruebas básicas sin los paquetes reales.

### Tests incluidos
- Endpoints principales (`actas.py`): `/actas/qr/`, `/actas/getconfig/`, `/actas/<uuid>/registerotp/`, `/actas/<uuid>/sendotp/`, `/actas/<uuid>/bfaresponse/`, `/actas/<uuid>/reject/`
- Operaciones (`operations/`): test básico para `sp_op_send_custom_totp_notification.run()`
- Management commands (`management/commands/`): test para `ucasal_documents_with_2thirds_of_state_sla_expired`

### Ejecutar todos los tests
En PowerShell:
```powershell
python manage.py test ucasal.tests
```
Esto ejecuta los tests de endpoints, operaciones y comandos usando los mocks.

### Notas
- Los tests están en `ucasal/tests/` y usan el sistema de tests de Django (`TestCase`).
- Los mocks permiten validar la estructura y el flujo, pero no la funcionalidad real de los servicios internos.
- Si agregas los paquetes reales, los tests usarán automáticamente esos paquetes en vez de los mocks.

## Resumen de pasos para desarrollo y testing

1. Instala dependencias:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Levanta la app localmente:
   ```powershell
   python manage.py runserver
   ```
3. Levanta la app con Docker:
   ```powershell
   docker-compose build --no-cache
   docker-compose up
   ```
4. Ejecuta los tests automáticos:
   ```powershell
   python manage.py test ucasal.tests
   ```

## Siguientes pasos recomendados
- Agregar más tests unitarios y de integración según avance el desarrollo.
- Reemplazar los mocks por los paquetes reales cuando estén disponibles.
- Ajustar rutas, settings y dependencias según el entorno de producción.
# Informe técnico y guía de arranque

Resumen: este repositorio contiene una aplicación Django (app `ucasal`) con endpoints HTTP para operaciones sobre "actas" (envío de OTP, validación, firma PDF y notificación a servicios externos). El código utiliza varias librerías internas prefijadas `sp_*` (logger, config, pdf signer, totp, etc.) que no están incluidas en este repo.

## Tecnología detectada
- Framework: Django (patterns de apps, urls, management commands)
- API: uso de Django REST Framework (decoradores en `utils.py`)
- Servicios HTTP: `requests` para comunicación con servicios externos (`external_services/ucasal/ucasal_services.py`)
- Otras: manejo de PDF, generación y verificación OTP, integración con servicios externos (UCASAL/BFA).

Dependencias externas (referenciadas pero no incluidas en el repo):
- sp_logger
- sp_athento_config
- sp_totp_generator
- sp_form_totp_notifier
- sp_pdf_otp_simple_signer

Estas parecen ser paquetes de la organización (privados). Para levantar la aplicación es necesario instalarlos o mockear su comportamiento.

## Diseño y arquitectura (alto nivel)
- Estructura: app `ucasal` con módulos:
  - `endpoints/` → definición de rutas y handlers (por ejemplo `actas.py`)
  - `external_services/ucasal/` → cliente HTTP hacia servicios UCASAL
  - `operations/` → operaciones que se ejecutan desde management commands
  - `management/commands/` → tareas periódicas o batch (p. ej. detectar actas con SLA casi vencida)
  - `utils.py` → utilidades comunes (decorators, config wrapper, constantes)
- Responsabilidades: los endpoints validan input, manipulan modelos (ej. `file.models.File`), llaman a servicios externos para OTP/QR/registro blockchain y actualizan metadatos y features del documento.

Puntos importantes y riesgos:
- Dependencia de paquetes internos `sp_*` (sin código en repo). Necesario para producción.
- Integración con UCASAL/BFA y otros servicios externos; algunos endpoints asumen respuestas JSON concretas.
- Operaciones que leen/escriben archivos físicos (ruta `/var/www/athentose/media/tmp/`) que deben existir en el contenedor/host.
- Uso de modelos externos (`file.models`, `doctypes.models`, `series.models`) que parecen pertenecer a una plataforma mayor (Athento). Requiere esa plataforma o mocks.

## Qué falta para ejecutar exactamente
1. No hay `manage.py` original ni settings globales. Añadí un `manage.py` y un `docker_settings.py` mínimo para pruebas locales.
2. Falta instalar paquetes internos `sp_*`. Opciones:
   - instalar los paquetes privados si están disponibles (pypi privado o wheel local)
   - o crear implementaciones de prueba (mocks) que satisfagan las funciones usadas
3. Falta la plataforma mayor (modelos `file.models`, etc.). Para pruebas limitadas puedes:
   - crear mocks de esos modelos o stubs que respondan a lo mínimo requerido por los endpoints
   - o ejecutar dentro del entorno de la plataforma Athento si la tienes.

## Ejecutar localmente (Windows PowerShell)
1) Crear y activar virtualenv
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2) Instalar dependencias internas (si tienes acceso)
   - pip install /path/to/sp_logger.whl ...

3) Ejecutar migraciones y levantar server de desarrollo
```powershell
python manage.py migrate
python manage.py runserver
```

Notas: con el `docker_settings.py` la base de datos por defecto es SQLite para pruebas sencillas.

## Ejecutar con Docker (recomendación básica)
1) Construir la imagen y levantar servicios:
```powershell
docker-compose build --no-cache
docker-compose up
```
2) La app quedará disponible en http://localhost:8000

Limitaciones con Docker:
- Para que los endpoints funcionen por completo necesitas proveer las dependencias `sp_*` y, probablemente, servicios externos (UCASAL) o stubs que las reemplacen.
- Rutas de archivos temporales usan `/var/www/athentose/media/tmp/` — debes mapear o crear esas carpetas dentro del contenedor o ajustar `docker_settings.MEDIA_TMP`.

## Próximos pasos sugeridos (priorizados)
1. Determinar cómo obtener los paquetes `sp_*` (registro interno o repositorios). Si existen, instálalos en `requirements.txt` o en la imagen Docker.
2. Si no están disponibles, implementar mocks mínimos para desarrollo (por ejemplo `ucasal/mocks/sp_logger.py`, `ucasal/mocks/sp_athento_config.py`) que imiten la API usada.
3. Añadir tests unitarios para endpoints críticos (`registerotp`, `bfaresponse`, `reject`) con los modelos y servicios mockeados.
4. Añadir un `Dockerfile` más completo y `docker-compose` que incluya servicios auxiliares reales (Postgres, Redis) si la plataforma lo requiere.

## Contacto
Si quieres, puedo:
- intentar crear mocks mínimos para las librerías internas y algunos modelos para permitir ejecutar los endpoints en modo demo (limitado)
- o preparar una imagen Docker completa si me indicas cómo obtener las dependencias privadas.
