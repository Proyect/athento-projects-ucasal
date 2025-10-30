from django.urls import re_path as url
from ucasal.utils import default_permissions, traceback_ret, encodeJSON, getJsonBody, decodeUTF8
from ucasal.utils import METHOD_NOT_ALLOWED
from ucasal.utils import TituloStates 
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger
from ucasal.utils import UcasalConfig
from django.http import HttpResponse
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


@default_permissions
@traceback_ret
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

        # Validaciones básicas
        if not filename:
            raise AthentoseError('El campo "filename" es requerido')
        if not file_obj:
            raise AthentoseError('El campo "file" es requerido (PDF del título)')
        if not doctype_name:
            raise AthentoseError('El campo "doctype" es requerido')
        if file_obj.content_type != 'application/pdf':
            raise AthentoseError(f'El archivo debe ser PDF. Recibido: {file_obj.content_type}')

        # Parsear filename: DNI/Lugar/SECTOR/CARRERA/MODO/PLAN
        filename_parts = filename.split('/')
        if len(filename_parts) != 6:
            raise AthentoseError(
                'filename debe tener formato: DNI/Lugar/SECTOR/CARRERA/MODO/PLAN. '
                f'Recibido: {filename}'
            )

        dni, lugar, sector, carrera, modo, plan = filename_parts

        # Validar componentes numéricos
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
        metadatas = {
            'metadata.titulo_tipo_dni': titulo_data.get('Tipo DNI', 'DNI'),
            'metadata.titulo_dni': titulo_data.get('DNI', dni),
            'metadata.titulo_lugar': titulo_data.get('Lugar', lugar),
            'metadata.titulo_lugar_id': lugar,
            'metadata.titulo_facultad': titulo_data.get('Facultad', sector),
            'metadata.titulo_facultad_id': sector,
            'metadata.titulo_carrera': titulo_data.get('Carrera', carrera),
            'metadata.titulo_carrera_id': carrera,
            'metadata.titulo_modalidad': titulo_data.get('Modalidad', modo),
            'metadata.titulo_modalidad_id': modo,
            'metadata.titulo_plan': titulo_data.get('Plan', plan),
            'metadata.titulo_titulo': titulo_data.get('Título', ''),
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

        # Autenticación Basic Auth
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

        # Obtener token y llamar a UCASAL
        auth_token = UcasalServices.get_auth_token(
            user=UcasalConfig.token_svc_user(),
            password=UcasalConfig.token_svc_password()
        )

        # Usar el mismo endpoint que actas (change_acta_svc_url funciona para títulos también)
        ucasal_url = f'{UcasalConfig.change_acta_svc_url()}/{uuid}'
        headers = {'Authorization': f'Bearer {auth_token}'}
        data = {'estado': estado_codigo}

        if observaciones:
            data['observaciones'] = observaciones

        logger.debug(f'Informando estado a UCASAL: {estado_codigo} para título {uuid}')

        response = requests.patch(ucasal_url, json=data, headers=headers, timeout=30)

        if response.status_code == requests.codes.ok:
            return logger.exit(HttpResponse(
                encodeJSON({
                    'success': True,
                    'uuid': str(uuid),
                    'estado': estado_descripcion,
                    'estado_codigo': estado_codigo,
                }),
                content_type='application/json'
            ))
        else:
            raise AthentoseError(f'Error en UCASAL: {response.status_code} - {response.text}')

    except FileNotFoundError as e:
        return logger.exit(HttpResponse(str(e), status=404), exc_info=True)
    except AthentoseError as e:
        return logger.exit(HttpResponse(str(e), status=400), exc_info=True)
    except Exception as e:
        return logger.exit(HttpResponse(str(e), status=500), exc_info=True)


@default_permissions
@traceback_ret
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
    """
    try:
        fil: File = None
        logger = SpLogger("ucasal", "titulos.bfaresponse")
        logger.entry()

        if request.method != 'POST':
            return logger.exit(METHOD_NOT_ALLOWED)
        
        body = getJsonBody(request)

        ## Validaciones

        # Validar 'status' del body
        result = body.get('status')
        if result not in ['success', 'failure']:
            raise AthentoseError(
                f"'status' debe ser 'success' o 'failure' en lugar de {result}"
            )
        
        # Validar existencia y doctype del UUID recibido
        fil = _get_titulo(uuid)
        if not fil:
            raise FileNotFoundError(f"El título '{uuid}' no existe")
        
        if not fil.doctype.name == titulo_doctype_name:
            raise AthentoseError(
                f"El documento con uuid '{uuid}' es de tipo '{fil.doctype.label}' "
                f"en lugar de 'Títulos'"
            )

        # Verificar estados válidos del título
        lifecycle_state = fil.life_cycle_state.name
        valid_states = [
            TituloStates.pendiente_blockchain,
            TituloStates.registrado_blockchain
        ]
        if not lifecycle_state in valid_states:
            raise AthentoseError(
                f"Sólo se puede registrar el resultado de blockchain si el título "
                f"se encuentra en los estados {' o '.join(valid_states)}, "
                f"pero el estado actual es '{lifecycle_state}'."
            )

        # Guardar fecha
        tz = pytz.timezone('America/Argentina/Buenos_Aires')
        date_str = datetime.now(tz=tz).strftime('%Y-%m-%d')

        # Registrar el sello como feature (tanto por éxito como error en BFA)
        fil.set_feature('bfa.result', encodeJSON(body))
        
        # Cambiar ciclo de vida 
        if result == 'success':
            # Notificar a UCASAL el registro exitoso en blockchain
            auth_token = UcasalServices.get_auth_token(
                user=UcasalConfig.token_svc_user(),
                password=UcasalConfig.token_svc_password()
            )
            UcasalServices.notify_blockchain_success(auth_token=auth_token, uuid=fil.uuid)
            
            fil.change_life_cycle_state(TituloStates.registrado_blockchain)
        else:
            fil.change_life_cycle_state(TituloStates.fallo_blockchain)

        fil.set_feature('registro.en.blockchain', result)

        return logger.exit(HttpResponse(
            'Resultado BFA guardado exitosamente'
        ))

    except FileNotFoundError as e:
        _save_bfaresponse_error_to_feature(fil)
        return logger.exit(HttpResponse(str(e), status='404'), exc_info=True)
    except AthentoseError as e:
        _save_bfaresponse_error_to_feature(fil)
        return logger.exit(HttpResponse(str(e), status='400'), exc_info=True)
    except Exception as e:
        _save_bfaresponse_error_to_feature(fil)
        raise logger.exit(HttpResponse(str(e), status='500'), exc_info=True)


def _get_pdf_hash(fil):
    """Calcula hash SHA256 del PDF. Igual que en actas."""
    path = fil.file.path
    byte_content = None
    with open(path, mode='rb') as f:
        byte_content = f.read()
    return hashlib.sha256(byte_content).hexdigest()


def _get_titulo(uuid: str):
    """
    Obtiene el título por UUID.
    Similar a _get_acta() en actas.
    """
    try:
        return File.objects.get(uuid=uuid)
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


routes = [
    url(r'^titulos/recibir/{0,1}$', recibir_titulo),
    url(r'^titulos/qr/{0,1}$', qr),
    url(r'^titulos/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/estado/{0,1}$', informar_estado),
    url(r'^titulos/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/validar-otp/{0,1}$', validar_otp),
    url(r'^titulos/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/bfaresponse/{0,1}$', bfaresponse),
]

