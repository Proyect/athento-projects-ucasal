from django.urls import re_path as url
from ucasal.utils import default_permissions, traceback_ret, encodeJSON, getJsonBody, decodeUTF8
from ucasal.utils import METHOD_NOT_ALLOWED
from ucasal.utils import TituloStates
from core.decorators import rate_limit_decorator 
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger
from ucasal.utils import UcasalConfig
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from model.File import File
from core.exceptions import AthentoseError
from external_services.ucasal.ucasal_services import UcasalServices
from ucasal.utils import titulo_doctype_name
from model.exceptions.invalid_otp_error import InvalidOtpError

from datetime import datetime
import pytz
import hashlib
from posixpath import join as urljoin
import os
import requests
import base64
from django.conf import settings
from django.core.files import File as FileObject
from tempfile import NamedTemporaryFile
import time
try:
    from ucasal.mocks.sp_pdf_otp_simple_signer import SpPdfSimpleSigner, QRInfo, OTPInfo
except ImportError:
    from ucasal.mocks.sp_pdf_otp_simple_signer import SpPdfSimpleSigner, QRInfo, OTPInfo
from core.metrics import (
    titulos_total, titulos_emitidos_total, titulos_tiempo_emision,
    titulos_cambios_estado, endpoint_titulos_recibir_total,
    endpoint_duration, ucasal_service_requests, ucasal_service_duration,
    ucasal_service_errors, errors_total
)


@default_permissions
@traceback_ret
@csrf_exempt
def recibir_titulo(request):
    """
    Recibe el PDF del título desde Decanato y lo crea en Athento.
    POST /titulos/recibir/
    
    Form-data:
    - filename: DNI/Lugar/SECTOR/CARRERA/MODO/PLAN (ej: 8205853/10/3/16/2/8707)
    - serie: títulos
    - doctype: títulos
    - file: PDF del título
    - json_data: (opcional) JSON con datos adicionales
    """
    try:
        logger = SpLogger("athentose", "titulos.recibir_titulo")
        logger.entry()

        if request.method != 'POST':
            return logger.exit(METHOD_NOT_ALLOWED)

        # Validar Content-Type
        content_type = request.content_type or ''
        if 'multipart/form-data' not in content_type:
            raise AthentoseError('Content-Type debe ser multipart/form-data')

        # Extraer datos del form-data
        filename = request.POST.get('filename')
        serie_name = request.POST.get('serie', 'títulos')
        doctype_name = request.POST.get('doctype', 'títulos')
        file_obj = request.FILES.get('file')
        json_data_raw = request.POST.get('json_data')

        # Validaciones básicas y construcción de filename si es necesario
        if not file_obj:
            raise AthentoseError('El campo "file" es requerido (PDF del título)')
        if not doctype_name:
            raise AthentoseError('El campo "doctype" es requerido')
        if file_obj.content_type != 'application/pdf':
            raise AthentoseError(f'El archivo debe ser PDF. Recibido: {file_obj.content_type}')

        def _digits_or_none(value):
            import re
            if not value:
                return None
            m = re.search(r"\((\d+)\)", str(value))
            if m:
                return m.group(1)
            only_digits = ''.join(ch for ch in str(value) if ch.isdigit())
            return only_digits or None

        def _get_any(keys):
            for k in keys:
                v = request.POST.get(k)
                if v:
                    return v
            return None

        def _try_build_filename():
            dni_v = _get_any(['dni', 'DNI', 'ndocu', 'NDOCU'])
            lugar_v = _get_any(['lugar', 'Lugar'])
            facultad_v = _get_any(['facultad', 'Facultad', 'sector', 'Sector'])
            carrera_v = _get_any(['carrera', 'Carrera'])
            modalidad_v = _get_any(['modalidad', 'Modalidad', 'modo', 'Modo'])
            plan_v = _get_any(['plan', 'Plan'])
            dni_v = ''.join(ch for ch in str(dni_v or '').strip() if ch.isdigit()) or None
            lugar_v = _digits_or_none(lugar_v)
            facultad_v = _digits_or_none(facultad_v)
            carrera_v = _digits_or_none(carrera_v)
            modalidad_v = _digits_or_none(modalidad_v)
            plan_v = _digits_or_none(plan_v)
            parts = [dni_v, lugar_v, facultad_v, carrera_v, modalidad_v, plan_v]
            if all(parts):
                return f"{dni_v}/{lugar_v}/{facultad_v}/{carrera_v}/{modalidad_v}/{plan_v}"
            return None

        def _is_valid_filename(name):
            parts = (name or '').split('/')
            if len(parts) != 6:
                return False
            try:
                _ = [int(p) for p in parts[1:]]
                if not parts[0] or not parts[0].isdigit():
                    return False
                return True
            except Exception:
                return False

        if not filename or not _is_valid_filename(filename):
            candidate = _try_build_filename()
            if candidate and _is_valid_filename(candidate):
                filename = candidate
            else:
                raise AthentoseError(
                    'filename debe tener formato: DNI/Lugar/SECTOR/CARRERA/MODO/PLAN o proveer campos (dni, lugar, facultad/sector, carrera, modalidad, plan) para construirlo.'
                )

        filename_parts = filename.split('/')
        dni, lugar, sector, carrera, modo, plan = filename_parts

        try:
            lugar_int = int(lugar)
            sector_int = int(sector)
            carrera_int = int(carrera)
            modo_int = int(modo)
            plan_int = int(plan)
        except ValueError as e:
            raise AthentoseError(f'Componentes del filename deben ser numéricos: {str(e)}')

        # Parsear JSON adicional si viene
        titulo_data = {}
        if json_data_raw:
            try:
                from ucasal.utils import decodeJSON
                titulo_data = decodeJSON(json_data_raw)
            except Exception as e:
                logger.debug(f'Error parseando json_data, usando valores por defecto: {e}')

        # Preparar metadatos para Athento (formato metadata.campo)
        tipo_dni_in = request.POST.get('tipo_dni') or request.POST.get('Tipo DNI') or titulo_data.get('Tipo DNI') or 'DNI'
        dni_in = request.POST.get('dni') or request.POST.get('DNI') or titulo_data.get('DNI', dni)
        lugar_in = request.POST.get('lugar') or request.POST.get('Lugar') or titulo_data.get('Lugar', lugar)
        facultad_in = request.POST.get('facultad') or request.POST.get('Facultad') or str(sector)
        carrera_in = request.POST.get('carrera') or request.POST.get('Carrera') or str(carrera)
        modalidad_in = request.POST.get('modalidad') or request.POST.get('Modalidad') or str(modo)
        plan_in = request.POST.get('plan') or request.POST.get('Plan') or str(plan)
        titulo_in = request.POST.get('titulo') or request.POST.get('Título') or titulo_data.get('Título', '')
        metadatas = {
            'metadata.titulo_tipo_dni': tipo_dni_in,
            'metadata.titulo_dni': dni_in,
            'metadata.titulo_lugar': lugar_in,
            'metadata.titulo_lugar_id': lugar,
            'metadata.titulo_facultad': facultad_in,
            'metadata.titulo_facultad_id': sector,
            'metadata.titulo_carrera': carrera_in,
            'metadata.titulo_carrera_id': carrera,
            'metadata.titulo_modalidad': modalidad_in,
            'metadata.titulo_modalidad_id': modo,
            'metadata.titulo_plan': plan_in,
            'metadata.titulo_titulo': titulo_in,
        }

        # Obtener configuración de Athento
        try:
            from ucasal.mocks.sp_athento_config import SpAthentoConfig as SAC
        except ImportError:
            from ucasal.mocks.sp_athento_config import SpAthentoConfig as SAC

        ATHENTO_BASE_URL = SAC.get_str('athento.base_url', default='https://ucasal-uat.athento.com')
        ATHENTO_API_USER = SAC.get_str('athento.api.user', default='ops.and.commands@athento.com')
        ATHENTO_API_PASSWORD = SAC.get_str('athento.api.password', is_secret=True, 
                                          default='U$7ujklo9#SP#UAT')

        # Preparar archivo
        file_obj.seek(0)
        file_content = file_obj.read()
        file_obj.seek(0)

        files = {
            'file': (
                file_obj.name or 'titulo.pdf',
                file_content,
                'application/pdf'
            )
        }

        # Preparar datos del form-data
        data = {
            'filename': filename,
            'doctype': doctype_name,
            'serie': serie_name,
        }

        # Agregar metadatos
        for key, value in metadatas.items():
            data[key] = str(value)

        # Pasar a través cualquier otro campo form-data recibido (ej. 'form_titulo')
        for key, value in request.POST.items():
            if key not in {'filename', 'doctype', 'serie', 'json_data'} and key not in data:
                data[key] = value

        # Autenticación Basic Auth (prioridad: header -> campos form -> configuración)
        incoming_auth = request.META.get('HTTP_AUTHORIZATION', '')
        form_user = request.POST.get('auth_user')
        form_pass = request.POST.get('auth_password')
        if incoming_auth.startswith('Basic '):
            headers = {'Authorization': incoming_auth}
        elif form_user and form_pass:
            credentials = base64.b64encode(
                f'{form_user}:{form_pass}'.encode()
            ).decode('utf-8')
            headers = {'Authorization': f'Basic {credentials}'}
        else:
            credentials = base64.b64encode(
                f'{ATHENTO_API_USER}:{ATHENTO_API_PASSWORD}'.encode()
            ).decode('utf-8')
            headers = {'Authorization': f'Basic {credentials}'}

        # Llamar a API de Athento
        athento_url = f'{ATHENTO_BASE_URL}/api/v1/file/'

        logger.debug(f'Creando título en Athento: {filename}')

        response = requests.post(
            athento_url,
            files=files,
            data=data,
            headers=headers,
            timeout=60
        )

        # Procesar respuesta
        if response.status_code in [200, 201]:
            try:
                response_data = response.json()
                documento_uuid = (
                    response_data.get('id') or
                    response_data.get('uuid') or
                    response_data.get('result', {}).get('uuid') or
                    response_data.get('result', {}).get('id')
                )
            except:
                documento_uuid = None

            logger.debug(f'Título creado en Athento: {documento_uuid}')

            return logger.exit(HttpResponse(
                encodeJSON({
                    'success': True,
                    'uuid': documento_uuid,
                    'filename': filename,
                    'doctype': doctype_name,
                    'serie': serie_name,
                }),
                content_type='application/json',
                status=201
            ))
        else:
            error_msg = f'Error en Athento (HTTP {response.status_code}): {response.text}'
            logger.error(error_msg)
            raise AthentoseError(error_msg)

    except AthentoseError as e:
        return logger.exit(HttpResponse(
            str(e),
            status=400
        ), exc_info=True)
    except Exception as e:
        return logger.exit(HttpResponse(
            str(e),
            status=500
        ), exc_info=True)


@default_permissions
@traceback_ret
def qr(request):
    """
    Genera código QR para títulos.
    POST /titulos/qr/
    Body: {"url": "https://..."}
    """
    from django.http import HttpResponse
    logger = SpLogger("athentose", "titulos.qr")
    logger.entry()
    
    if request.method != 'POST':
        return logger.exit(METHOD_NOT_ALLOWED)
    
    body = getJsonBody(request)
    url = body.get('url', 'https://example.com')

    bytes = UcasalServices.get_qr_image(url=url)

    return HttpResponse(
        bytes,
        content_type="image/png"
    )


@default_permissions
@traceback_ret
def informar_estado(request, uuid):
    """
    Informa cambios de estado del título a UCASAL.
    POST /titulos/{uuid}/estado/
    Body: {"estado": "Aprobado por UA", "observaciones": "..."}
    """
    try:
        logger = SpLogger("athentose", "titulos.informar_estado")
        logger.entry()

        if request.method != 'POST':
            return logger.exit(METHOD_NOT_ALLOWED)

        body = getJsonBody(request)
        estado_descripcion = body.get('estado')
        observaciones = body.get('observaciones', '')

        if not estado_descripcion:
            raise AthentoseError('El campo "estado" es requerido')

        # Validar que el título existe y es del doctype correcto
        fil = _get_titulo(uuid)
        if not fil:
            raise FileNotFoundError(f"El título '{uuid}' no existe")

        if not fil.doctype.name == titulo_doctype_name:
            raise AthentoseError(
                f"El documento con uuid '{uuid}' es de tipo '{fil.doctype.label}' "
                f"en lugar de 'Títulos'"
            )

        # Mapear estado a código UCASAL (similar a actas)
        estado_map = {
            TituloStates.recibido: 0,
            TituloStates.pendiente_aprobacion_ua: 1,
            TituloStates.aprobado_ua: 2,
            TituloStates.pendiente_aprobacion_r: 3,
            TituloStates.aprobado_r: 4,
            TituloStates.pendiente_firma_sg: 5,
            TituloStates.firmado_sg: 6,
            TituloStates.titulo_emitido: 7,
            TituloStates.rechazado: 99,
        }

        estado_codigo = estado_map.get(estado_descripcion, 0)

        # Obtener token y llamar a UCASAL a través del servicio (mockeable)
        auth_token = UcasalServices.get_auth_token(
            user=UcasalConfig.token_svc_user(),
            password=UcasalConfig.token_svc_password()
        )

        logger.debug(f'Informando estado a UCASAL: {estado_codigo} para título {uuid}')

        notify_resp = UcasalServices.notify_titulo_estado(
            auth_token=auth_token,
            uuid=str(uuid),
            estado=estado_codigo,
            observaciones=observaciones or ''
        )

        if True:  # notify_titulo_estado lanza excepción si falla
            # Obtener estado anterior antes de cambiar
            estado_anterior = fil.life_cycle_state.name if fil.life_cycle_state else fil.life_cycle_state_legacy
            
            # Cambiar estado del documento si es necesario
            from model.File import LifeCycleState
            try:
                nuevo_estado_obj, _ = LifeCycleState.objects.get_or_create(name=estado_descripcion)
                fil.change_life_cycle_state(nuevo_estado_obj)
                logger.debug(f'Estado del título {uuid} cambiado a {estado_descripcion}')
            except Exception as e:
                logger.warning(f'No se pudo cambiar estado del título {uuid}: {e}')
            
            # Enviar notificación de cambio de estado
            try:
                _notificar_cambio_estado_titulo(fil, estado_anterior, estado_descripcion, observaciones, logger)
            except Exception as e:
                # No fallar el endpoint si la notificación falla, solo loguear
                logger.warning(f'Error enviando notificación de cambio de estado para título {uuid}: {e}', exc_info=True)
            
            return logger.exit(HttpResponse(
                encodeJSON({
                    'success': True,
                    'uuid': str(uuid),
                    'estado': estado_descripcion,
                    'estado_codigo': estado_codigo,
                }),
                content_type='application/json'
            ))
        

    except FileNotFoundError as e:
        return logger.exit(HttpResponse(str(e), status=404), exc_info=True)
    except AthentoseError as e:
        return logger.exit(HttpResponse(str(e), status=400), exc_info=True)
    except Exception as e:
        return logger.exit(HttpResponse(str(e), status=500), exc_info=True)


@default_permissions
@traceback_ret
@rate_limit_decorator(key='ip', rate='10/m', method='POST')  # 10 requests por minuto por IP
def validar_otp(request, uuid):
    """
    Valida token OTP para firma del título.
    POST /titulos/{uuid}/validar-otp/
    Body: {"otp": "123456", "usuario": "usuario@ucasal.edu.ar"}
    """
    try:
        logger = SpLogger("athentose", "titulos.validar_otp")
        logger.entry()

        if request.method != 'POST':
            return logger.exit(METHOD_NOT_ALLOWED)

        body = getJsonBody(request)
        otp = str(body.get('otp', ''))
        usuario = body.get('usuario')

        # Validar OTP
        if not _is_digit(otp):
            raise AthentoseError(f"'otp' debe ser un número entero positivo en lugar de '{otp}'")

        otp = int(otp)

        if not usuario:
            raise AthentoseError("'usuario' es requerido")

        if not _is_non_empty_string(usuario):
            raise AthentoseError(f"El usuario debe ser un string no vacío en lugar de '{usuario}'")

        # Validar título existe
        fil = _get_titulo(uuid)
        if not fil:
            raise FileNotFoundError(f'El título {uuid} no existe')

        if not fil.doctype.name == titulo_doctype_name:
            raise AthentoseError(
                f"El documento con uuid '{uuid}' es de tipo '{fil.doctype.label}' "
                f"en lugar de 'Títulos'"
            )

        # Validar OTP con servicio UCASAL
        UcasalServices.validate_otp(user=usuario, otp=otp)

        return logger.exit(HttpResponse(
            encodeJSON({
                'otp_valido': True,
                'usuario': usuario,
                'uuid': str(uuid)
            }),
            content_type='application/json'
        ))

    except FileNotFoundError as e:
        return logger.exit(HttpResponse(str(e), status=404), exc_info=True)
    except AthentoseError as e:
        return logger.exit(HttpResponse(str(e), status=400), exc_info=True)
    except InvalidOtpError as e:
        return logger.exit(HttpResponse(str(e), status=400), exc_info=True)
    except Exception as e:
        return logger.exit(HttpResponse(str(e), status=500), exc_info=True)


@default_permissions
@traceback_ret
def bfaresponse(request, uuid):
    """
    Callback desde blockchain (BFA) cuando se registra el título.
    POST /titulos/{uuid}/bfaresponse/
    Body: {"status": "success" o "failure", ...}
    
    NOTA: Este endpoint está SUSPENDIDO temporalmente.
    La funcionalidad de blockchain para títulos ha sido deshabilitada.
    Se implementará firma digital en su lugar.
    
    TODO: Reimplementar cuando se defina el nuevo flujo de firma digital.
    """
    try:
        logger = SpLogger("ucasal", "titulos.bfaresponse")
        logger.entry()

        if request.method != 'POST':
            return logger.exit(METHOD_NOT_ALLOWED)
        
        # Endpoint suspendido - retornar error informativo
        error_msg = (
            "El endpoint de blockchain para títulos está suspendido temporalmente. "
            "Se implementará firma digital en su lugar. "
            "Para más información, consulte la documentación."
        )
        logger.warning(f"Intento de usar endpoint suspendido bfaresponse para título {uuid}")
        
        return logger.exit(HttpResponse(
            encodeJSON({
                'error': 'Endpoint suspendido',
                'message': error_msg,
                'status': 'blockchain_suspended'
            }),
            content_type='application/json',
            status=503  # Service Unavailable
        ))

    except Exception as e:
        logger = SpLogger("ucasal", "titulos.bfaresponse")
        return logger.exit(HttpResponse(str(e), status=500), exc_info=True)


def _notificar_cambio_estado_titulo(fil, estado_anterior, estado_nuevo, observaciones='', logger=None):
    """
    Helper para notificar cambio de estado de un título.
    
    Args:
        fil: Objeto File del título
        estado_anterior: Estado anterior del título
        estado_nuevo: Estado nuevo del título
        observaciones: Observaciones opcionales
        logger: Logger opcional
    """
    if logger is None:
        logger = SpLogger("athentose", "titulos._notificar_cambio_estado_titulo")
    
    try:
        from operations.ucasal_titulo_notificar_cambio_estado import UcasalTituloNotificarCambioEstado
        
        # Determinar template según el estado
        template_map = {
            TituloStates.pendiente_aprobacion_ua: 'ucasal_titulo_pendiente_aprobacion',
            TituloStates.pendiente_aprobacion_r: 'ucasal_titulo_pendiente_aprobacion',
            TituloStates.pendiente_firma_sg: 'ucasal_titulo_listo_firma',
            TituloStates.firmado_sg: 'ucasal_titulo_firmado',
            TituloStates.titulo_emitido: 'ucasal_titulo_emitido',
            TituloStates.rechazado: 'ucasal_titulo_rechazado',
        }
        
        # Usar template específico o genérico
        template = template_map.get(estado_nuevo, 'ucasal_titulo_estado_cambiado')
        
        # Ejecutar operación de notificación
        # Los parámetros se pasan como kwargs al constructor
        operation = UcasalTituloNotificarCambioEstado(
            document=fil,
            notifications_template=template,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            observaciones=observaciones
        )
        
        result = operation.run()
        logger.debug(f'Notificación de cambio de estado enviada: {result}')
        
    except Exception as e:
        logger.error(f'Error en _notificar_cambio_estado_titulo: {e}', exc_info=True)
        raise


def _get_pdf_hash(fil):
    """Calcula hash SHA256 del PDF. Igual que en actas."""
    path = fil.file.path
    byte_content = None
    with open(path, mode='rb') as f:
        byte_content = f.read()
    return hashlib.sha256(byte_content).hexdigest()


def _get_titulo(uuid: str):
    """
    Helper para obtener título por UUID con optimización.
    Similar a _get_acta() en actas.
    """
    try:
        return File.objects.select_related('doctype_obj', 'life_cycle_state_obj', 'serie').get(uuid=uuid)
    except File.DoesNotExist:
        return None


def _save_bfaresponse_error_to_feature(fil: File):
    """
    Guarda error en feature del documento.
    Igual que en actas.
    """
    import traceback as tb
    if fil:
        fil.set_feature('svc.bfaresponse.error', tb.format_exc())


def _is_non_empty_string(value: str):
    """Helper igual que en actas."""
    return isinstance(value, str) and value.strip() != ""


def _is_digit(value: str):
    """Helper igual que en actas."""
    return isinstance(value, str) and value.isdigit()


def _get_arg_time():
    """Obtiene la fecha y hora actual formateada."""
    argentina_timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    current_time = datetime.now(argentina_timezone)
    formatted_time = current_time.strftime('%d/%m/%Y %H:%M:%S')
    return formatted_time


def _delete_file(file_path):
    """Elimina un archivo si existe."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        pass  # No fallar si no se puede eliminar


@default_permissions
@traceback_ret
@rate_limit_decorator(key='ip', rate='5/m', method='POST')  # 5 requests por minuto por IP
def firmar_titulo(request, uuid):
    """
    Firma digitalmente un título incrustando QR e información de firma.
    POST /titulos/{uuid}/firmar/
    Body: {
        "otp": 123456,  // Opcional
        "ip": "192.168.1.1",
        "latitude": -34.6037,
        "longitude": -58.3816,
        "accuracy": "10m",
        "user_agent": "Mozilla/5.0..."
    }
    """
    start_time = time.time()
    try:
        logger = SpLogger("athentose", "titulos.firmar_titulo")
        logger.entry()

        if request.method != 'POST':
            endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)
            return logger.exit(METHOD_NOT_ALLOWED)

        body = getJsonBody(request)

        # Validar que el título existe y es del doctype correcto
        fil = _get_titulo(uuid)
        if not fil:
            endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)
            errors_total.labels(error_type='FileNotFoundError', endpoint='firmar_titulo').inc()
            raise FileNotFoundError(f"El título '{uuid}' no existe")

        if not fil.doctype.name == titulo_doctype_name:
            endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)
            errors_total.labels(error_type='AthentoseError', endpoint='firmar_titulo').inc()
            raise AthentoseError(
                f"El documento con uuid '{uuid}' es de tipo '{fil.doctype.label}' "
                f"en lugar de 'Títulos'"
            )

        # Validar que el título está en estado "Pendiente Firma SG"
        lifecycle_state = fil.life_cycle_state.name if fil.life_cycle_state else fil.life_cycle_state_legacy
        if lifecycle_state != TituloStates.pendiente_firma_sg:
            endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)
            errors_total.labels(error_type='AthentoseError', endpoint='firmar_titulo').inc()
            raise AthentoseError(
                f"Sólo se puede firmar el título si se encuentra en estado '{TituloStates.pendiente_firma_sg}', "
                f"pero el estado actual es '{lifecycle_state}'."
            )

        # Validar que el PDF existe
        if not fil.file or not os.path.exists(fil.file.path):
            endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)
            errors_total.labels(error_type='AthentoseError', endpoint='firmar_titulo').inc()
            raise AthentoseError(f"El PDF del título no existe o no está disponible")

        # Validar OTP si se proporciona (opcional para títulos)
        otp = body.get('otp')
        if otp:
            otp = str(otp)
            if not _is_digit(otp):
                raise AthentoseError(f"'otp' debe ser un número entero positivo en lugar de '{otp}'")
            otp = int(otp)
            
            # Validar OTP con servicio UCASAL
            usuario_sg = body.get('usuario', 'secretaria.general@ucasal.edu.ar')
            service_start = time.time()
            try:
                UcasalServices.validate_otp(user=usuario_sg, otp=otp)
                ucasal_service_requests.labels(service='validate_otp', status='success').inc()
            except InvalidOtpError:
                ucasal_service_requests.labels(service='validate_otp', status='error').inc()
                ucasal_service_errors.labels(service='validate_otp', error_type='InvalidOtpError').inc()
                raise
            finally:
                ucasal_service_duration.labels(service='validate_otp').observe(time.time() - service_start)

        # Obtener token de autenticación de UCASAL
        service_start = time.time()
        try:
            auth_token = UcasalServices.get_auth_token(
                user=UcasalConfig.token_svc_user(),
                password=UcasalConfig.token_svc_password()
            )
            ucasal_service_requests.labels(service='get_auth_token', status='success').inc()
        except Exception as e:
            ucasal_service_requests.labels(service='get_auth_token', status='error').inc()
            ucasal_service_errors.labels(service='get_auth_token', error_type=type(e).__name__).inc()
            raise
        finally:
            ucasal_service_duration.labels(service='get_auth_token').observe(time.time() - service_start)

        # Validar campos opcionales para metadata
        ip = body.get('ip', '')
        latitude = body.get('latitude')
        longitude = body.get('longitude')
        accuracy = body.get('accuracy', '')
        user_agent = body.get('user_agent', '')

        # Generar URL de validación y acortarla
        url_to_shorten = UcasalConfig.titulo_validation_url_template().replace('{{uuid}}', str(fil.uuid))
        service_start = time.time()
        try:
            short_url = UcasalServices.get_short_url(auth_token=auth_token, url=url_to_shorten)
            ucasal_service_requests.labels(service='get_short_url', status='success').inc()
        except Exception as e:
            ucasal_service_requests.labels(service='get_short_url', status='error').inc()
            ucasal_service_errors.labels(service='get_short_url', error_type=type(e).__name__).inc()
            raise
        finally:
            ucasal_service_duration.labels(service='get_short_url').observe(time.time() - service_start)

        # Obtener imagen QR
        service_start = time.time()
        try:
            qr_stream = UcasalServices.get_qr_image(url=short_url)
            ucasal_service_requests.labels(service='get_qr_image', status='success').inc()
        except Exception as e:
            ucasal_service_requests.labels(service='get_qr_image', status='error').inc()
            ucasal_service_errors.labels(service='get_qr_image', error_type=type(e).__name__).inc()
            raise
        finally:
            ucasal_service_duration.labels(service='get_qr_image').observe(time.time() - service_start)

        # Guardar imagen QR temporalmente
        qr_image_tmp_path = os.path.join(settings.MEDIA_TMP, f'ucasal_qr_titulo_{fil.uuid}.png')
        os.makedirs(settings.MEDIA_TMP, exist_ok=True)
        with open(qr_image_tmp_path, 'wb') as qr_file:
            qr_file.write(qr_stream)

        # Obtener información del título para el texto de firma
        dni = fil.gmv('metadata.titulo_dni') or 'N/A'
        titulo_nombre = fil.gmv('metadata.titulo_titulo') or fil.titulo or 'Título Universitario'
        fecha_firma = _get_arg_time()
        
        # Generar texto de firma
        texto_firma = f"""Firmado digitalmente por:
Secretaría General - UCASAL
Fecha: {fecha_firma}
Título: {titulo_nombre}
DNI: {dni}"""

        # Crear QRInfo
        qr_info = QRInfo(
            image_path=qr_image_tmp_path,
            image_text=texto_firma,
            x=10, y=10, width=40, height=40  # Coordenadas en puntos
        )

        # Crear OTPInfo si hay información disponible
        otp_info = None
        if ip and latitude is not None and longitude is not None:
            otp_info = OTPInfo(
                mail='secretaria.general@ucasal.edu.ar',
                ip=ip,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy,
                user_agent=user_agent
            )

        # Incrustar QR e información en el PDF
        signer = SpPdfSimpleSigner()
        pdf_out_stream = signer.sign(
            input_pdf_path=fil.file.path,
            qr_info=qr_info,
            otp_info=otp_info
        )

        # Borrar la imagen temporal del QR
        _delete_file(qr_image_tmp_path)

        # Actualizar binario del título en Athento
        with NamedTemporaryFile(dir=settings.MEDIA_TMP, suffix='.ucasal.tmp') as pdf_temp:
            pdf_out_stream.seek(0)
            pdf_temp.write(pdf_out_stream.read())
            pdf_temp.seek(0)
            fil.update_binary(FileObject(pdf_temp), fil.filename + ".pdf")

        # Guardar metadata de firma
        fil.set_feature('firmada.digital', "1")
        fil.set_metadata('metadata.firma.fecha', fecha_firma)
        fil.set_metadata('metadata.firma.firmante', 'Secretaría General')
        fil.set_metadata('metadata.firma.url_validacion', short_url)
        if ip:
            fil.set_metadata('metadata.firma.ip', ip)

        # Cambiar estado a "Firmado por SG"
        from model.File import LifeCycleState
        firmado_state_obj, _ = LifeCycleState.objects.get_or_create(name=TituloStates.firmado_sg)
        fil.change_life_cycle_state(firmado_state_obj)

        # Guardar fecha de firma
        tz = pytz.timezone('America/Argentina/Buenos_Aires')
        fecha_firma_date = datetime.now(tz=tz).strftime('%Y-%m-%d')
        fil.set_metadata('metadata.titulo_fecha_firma', fecha_firma_date)

        # Métricas
        titulos_cambios_estado.labels(
            estado_anterior=TituloStates.pendiente_firma_sg,
            estado_nuevo=TituloStates.firmado_sg
        ).inc()
        endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)

        # Enviar notificación de firma
        try:
            _notificar_cambio_estado_titulo(
                fil, 
                TituloStates.pendiente_firma_sg, 
                TituloStates.firmado_sg, 
                f'Título firmado digitalmente el {fecha_firma}. URL de validación: {short_url}',
                logger
            )
        except Exception as e:
            # No fallar el endpoint si la notificación falla, solo loguear
            logger.warning(f'Error enviando notificación de firma para título {uuid}: {e}', exc_info=True)

        logger.debug(f'Título {uuid} firmado exitosamente')

        return logger.exit(HttpResponse(
            encodeJSON({
                'success': True,
                'message': 'Título firmado exitosamente',
                'uuid': str(uuid),
                'estado': TituloStates.firmado_sg,
                'fecha_firma': fecha_firma,
                'url_validacion': short_url
            }),
            content_type='application/json'
        ))

    except FileNotFoundError as e:
        endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)
        errors_total.labels(error_type='FileNotFoundError', endpoint='firmar_titulo').inc()
        return logger.exit(HttpResponse(str(e), status=404), exc_info=True)
    except AthentoseError as e:
        endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)
        errors_total.labels(error_type='AthentoseError', endpoint='firmar_titulo').inc()
        return logger.exit(HttpResponse(str(e), status=400), exc_info=True)
    except InvalidOtpError as e:
        endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)
        errors_total.labels(error_type='InvalidOtpError', endpoint='firmar_titulo').inc()
        return logger.exit(HttpResponse(str(e), status=400), exc_info=True)
    except Exception as e:
        endpoint_duration.labels(endpoint='firmar_titulo', method='POST').observe(time.time() - start_time)


def _form_html(base_url: str):
    return '''<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Subir Título</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: system-ui, sans-serif; margin: 20px; max-width: 900px; }
    fieldset { margin-bottom: 16px; }
    label { display:block; margin: 6px 0 2px; }
    input, select { width: 100%; padding: 8px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .row3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
    .hint { font-size: 12px; color: #666; }
    .ok { color: #0a0; }
    .err { color: #a00; white-space: pre-wrap; }
    button { padding: 10px 16px; }
    .grid { display:grid; gap:8px; }
    .actions { display:flex; gap: 8px; align-items:center; }
  </style>
</head>
<body>
  <h1>Subir Título</h1>
  <p class="hint">Este formulario arma automáticamente el nombre de archivo con el formato DNI/Lugar/SECTOR/CARRERA/MODO/PLAN y lo envía al endpoint <code>/titulos/recibir/</code>.</p>

  <form id="f" class="grid" action="{base_url}/titulos/recibir/" method="post" enctype="multipart/form-data">
    <fieldset>
      <legend>Autenticación Athento (opcional)</legend>
      <div class="row">
        <div>
          <label>Usuario (Basic)</label>
          <input name="auth_user" type="text" placeholder="usuario@ucasal.edu.ar" />
        </div>
        <div>
          <label>Contraseña (Basic)</label>
          <input name="auth_password" type="password" />
        </div>
      </div>
      <p class="hint">Si no completa, se usarán las credenciales configuradas del sistema.</p>
    </fieldset>

    <fieldset>
      <legend>Datos del Título</legend>
      <div class="row3">
        <div>
          <label>Tipo DNI</label>
          <select name="tipo_dni">
            <option value="DNI">DNI</option>
            <option value="LE">LE</option>
            <option value="LC">LC</option>
          </select>
        </div>
        <div>
          <label>DNI</label>
          <input name="dni" required placeholder="8205853" />
        </div>
        <div>
          <label>Título</label>
          <input name="titulo" placeholder="Abogado" />
        </div>
      </div>

      <label>Lugar</label>
      <input name="lugar" placeholder="DELEGACION S S DE JUJUY - JUJUY (10)" />

      <label>Facultad</label>
      <input name="facultad" placeholder="CIENCIAS JURÍDICAS (3)" />

      <div class="row3">
        <div>
          <label>Carrera</label>
          <input name="carrera" placeholder="Abogacia (16)" />
        </div>
        <div>
          <label>Modalidad</label>
          <input name="modalidad" placeholder="NO PRESENCIAL (2)" />
        </div>
        <div>
          <label>Plan</label>
          <input name="plan" placeholder="8707" />
        </div>
      </div>

      <div class="row">
        <div>
          <label>Doctype</label>
          <input name="doctype" value="títulos" />
          <p class="hint">Se respeta el valor que ingrese (no se modifica).</p>
        </div>
        <div>
          <label>Serie</label>
          <input name="serie" placeholder="2320305d-3169-464f-a7ea-76a2c62d79c0" />
        </div>
      </div>

      <label>Archivo PDF</label>
      <input name="file" type="file" accept="application/pdf" required />

      <input type="hidden" name="filename" id="filename" />
      <div class="actions">
        <label><input type="checkbox" id="remember" checked /> Recordar estos valores</label>
        <button type="button" id="clearStored" title="Eliminar valores recordados">Limpiar recordados</button>
      </div>
      <p class="hint">El nombre se construirá automáticamente al enviar.</p>
    </fieldset>

    <button type="submit">Subir</button>
    <div id="msg" class="hint"></div>
  </form>

  <script>
    const f = document.getElementById('f');
    const msg = document.getElementById('msg');
    const remember = document.getElementById('remember');
    const clearBtn = document.getElementById('clearStored');

    // Campos a persistir (excluye contraseñas)
    const fields = ['tipo_dni','dni','titulo','lugar','facultad','carrera','modalidad','plan','doctype','serie','auth_user'];
    const storageKey = 'ucasal_titulos_form_v1';

    function loadStored() {
      try {
        const raw = localStorage.getItem(storageKey);
        if (!raw) return;
        const data = JSON.parse(raw);
        fields.forEach(k => {
          if (data[k] != null && f[k]) {
            if (f[k].tagName === 'SELECT') {
              [...f[k].options].forEach(opt => { if (opt.value === data[k]) opt.selected = true; });
            } else {
              f[k].value = data[k];
            }
          }
        });
      } catch (e) { /* ignore */ }
    }

    function saveStored() {
      try {
        const data = {};
        fields.forEach(k => { if (f[k]) data[k] = f[k].value; });
        localStorage.setItem(storageKey, JSON.stringify(data));
      } catch (e) { /* ignore */ }
    }

    function clearStored() {
      try { localStorage.removeItem(storageKey); } catch (e) { /* ignore */ }
    }

    function digitsFrom(value) {
      if (!value) return '';
      const m = String(value).match(/\((\d+)\)/);
      if (m) return m[1];
      return String(value).replace(/\D+/g, '');
    }

    // Prefill al cargar
    loadStored();

    // Guardar/limpiar según checkbox
    f.addEventListener('change', () => { if (remember.checked) saveStored(); });
    clearBtn.addEventListener('click', () => { clearStored(); msg.textContent = 'Valores recordados eliminados.'; });

    f.addEventListener('submit', (e) => {
      const dni = digitsFrom(f.dni.value);
      const lugar = digitsFrom(f.lugar.value);
      const facultad = digitsFrom(f.facultad.value);
      const carrera = digitsFrom(f.carrera.value);
      const modalidad = digitsFrom(f.modalidad.value);
      const plan = digitsFrom(f.plan.value);
      const parts = [dni, lugar, facultad, carrera, modalidad, plan];
      if (parts.some(p => !p)) {
        e.preventDefault();
        msg.className = 'err';
        msg.textContent = 'Complete DNI/Lugar/Facultad/Carrera/Modalidad/Plan (deben ser numéricos o incluir el código entre paréntesis).';
        return;
      }
      document.getElementById('filename').value = parts.join('/');
      if (remember.checked) saveStored();
      msg.className = 'ok';
      msg.textContent = 'Enviando...';
    });
  </script>
  </body>
</html>'''.replace('{base_url}', base_url)

@default_permissions
@traceback_ret
@csrf_exempt
def form_subir_titulo(request):
    try:
        logger = SpLogger("athentose", "titulos.form_subir_titulo")
        logger.entry()
        if request.method != 'GET':
            return logger.exit(METHOD_NOT_ALLOWED)
        base_url = ''
        try:
            from django.conf import settings as djsettings
            base_url = djsettings.BASE_URL if hasattr(djsettings, 'BASE_URL') else ''
        except Exception:
            base_url = ''
        html = _form_html(base_url)
        return logger.exit(HttpResponse(html, content_type='text/html'))
    except Exception as e:
        return logger.exit(HttpResponse(str(e), status=500), exc_info=True)

routes = [
    url(r'^titulos/form/{0,1}$', form_subir_titulo),
    url(r'^titulos/recibir/{0,1}$', recibir_titulo),
    url(r'^titulos/qr/{0,1}$', qr),
    url(r'^titulos/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/estado/{0,1}$', informar_estado),
    url(r'^titulos/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/validar-otp/{0,1}$', validar_otp),
    url(r'^titulos/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/firmar/{0,1}$', firmar_titulo),
    url(r'^titulos/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/bfaresponse/{0,1}$', bfaresponse),
]

