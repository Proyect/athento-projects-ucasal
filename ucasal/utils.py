from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
#from core.exceptions import AthentoseError
from json import loads as decodeJSON, dumps as encodeJSON
import traceback
try:
    # Intentar importar implementación real desde ucasal
    from ucasal.sp_athento_config import SpAthentoConfig as SAC
except ImportError:
    try:
        # Intentar importar desde path raíz (para compatibilidad)
        from sp_athento_config import SpAthentoConfig as SAC
    except ImportError:
        # Fallback a mock si no hay implementación real
        from ucasal.mocks.sp_athento_config import SpAthentoConfig as SAC
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger


NOT_FOUND = HttpResponse('Provider not found.', status=404)
BAD_REQUEST = HttpResponse('Bad request', status=400)
UNAUTHORIZED = HttpResponse('Unauthorized access.', status=401)
FORBIDDEN = HttpResponse('Forbidden access.', status=403)
METHOD_NOT_ALLOWED = HttpResponse('Method not allowed.', status=405)

_totp_base_key = '63f4d2f816aab7c7945278bce5bfc755'

NoneType = type(None)
serializableJsonTypes = (int, str, float, bool, NoneType)

automation_user = 'ops.and.commands@athento.com'

# Nombres de campos de Acta
sector_metadata_name = 'metadata.acta_cod_sector'
nro_revision_metadata_name =  'metadata.acta_nro_revision'
uuid_previo_metadata_name =  'metadata.acta_id_acta_previa'
serie_actas_revisadas_name = 'actas_revisadas'

# Nombre del doctype del Acta
acta_examen_doctype_name = 'acta'

# Nombres de campos de Título
titulo_tipo_dni_metadata_name = 'metadata.titulo_tipo_dni'
titulo_dni_metadata_name = 'metadata.titulo_dni'
titulo_lugar_metadata_name = 'metadata.titulo_lugar'
titulo_lugar_id_metadata_name = 'metadata.titulo_lugar_id'
titulo_facultad_metadata_name = 'metadata.titulo_facultad'
titulo_facultad_id_metadata_name = 'metadata.titulo_facultad_id'
titulo_carrera_metadata_name = 'metadata.titulo_carrera'
titulo_carrera_id_metadata_name = 'metadata.titulo_carrera_id'
titulo_modalidad_metadata_name = 'metadata.titulo_modalidad'
titulo_modalidad_id_metadata_name = 'metadata.titulo_modalidad_id'
titulo_plan_metadata_name = 'metadata.titulo_plan'
titulo_titulo_metadata_name = 'metadata.titulo_titulo'

# Nombre del doctype del Título
titulo_doctype_name = 'títulos'

# Nombres de series de Títulos
serie_titulos_name = 'títulos'
serie_titulos_pendiente_ua_name = 'títulos_pendiente_ua'
serie_titulos_pendiente_rector_name = 'títulos_pendiente_rector'
serie_titulos_pendiente_sg_name = 'títulos_pendiente_sg'
serie_titulos_emitidos_name = 'títulos_emitidos'
serie_titulos_rechazados_name = 'títulos_rechazados'


class ActaStates:
    recibida = 'Recibida'
    pendiente_otp = 'Pendiente Firma OTP'
    pendiente_blockchain = 'Pendiente Blockchain'
    firmada = 'Firmada'
    fallo_blockchain = 'Fallo en Blockchain'
    rechazada = 'Rechazada'

class TituloStates:
    recibido = 'Recibido'
    pendiente_aprobacion_ua = 'Pendiente Aprobación UA'
    aprobado_ua = 'Aprobado por UA'
    pendiente_aprobacion_r = 'Pendiente Aprobación R'
    aprobado_r = 'Aprobado por R'
    pendiente_firma_sg = 'Pendiente Firma SG'
    firmado_sg = 'Firmado por SG'
    # Estados de blockchain SUSPENDIDOS temporalmente - se implementará firma digital
    # TODO: Revisar cuando se implemente la firma digital
    pendiente_blockchain = 'Pendiente Blockchain'  # DEPRECATED: suspendido temporalmente
    registrado_blockchain = 'Registrado en Blockchain'  # DEPRECATED: suspendido temporalmente
    titulo_emitido = 'Título Emitido'
    rechazado = 'Rechazado'

TITULO_TRANSITIONS_ALLOWED = {
    TituloStates.recibido: [TituloStates.pendiente_aprobacion_ua, TituloStates.rechazado],
    TituloStates.pendiente_aprobacion_ua: [TituloStates.aprobado_ua, TituloStates.rechazado],
    TituloStates.aprobado_ua: [TituloStates.pendiente_aprobacion_r, TituloStates.rechazado],
    TituloStates.pendiente_aprobacion_r: [TituloStates.aprobado_r, TituloStates.rechazado],
    TituloStates.aprobado_r: [TituloStates.pendiente_firma_sg, TituloStates.rechazado],
    TituloStates.pendiente_firma_sg: [TituloStates.firmado_sg, TituloStates.rechazado],
    TituloStates.firmado_sg: [TituloStates.titulo_emitido],
    TituloStates.titulo_emitido: [],
    TituloStates.rechazado: [],
}

TITULO_ESTADO_CODIGO = {
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

def can_transition(from_state: str, to_state: str) -> bool:
    options = TITULO_TRANSITIONS_ALLOWED.get(from_state) or []
    return to_state in options

class AthentoseError(Exception):
    pass

class UcasalConfig:
    @staticmethod
    def token_svc_url()->str:
        return SAC.get_str('ucasal.endpoint.gettoken.url')     

    @staticmethod
    def token_svc_user()->str:
        return SAC.get_str('ucasal.endpoint.gettoken.usuario')     

    @staticmethod
    def token_svc_password()->str:
        return SAC.get_str('ucasal.endpoint.gettoken.clave', is_secret=True)     
    
    @staticmethod
    def otp_validity_seconds()->int:
        return SAC.get_int('ucasal.otp_validity_seconds')         

    @staticmethod
    def qr_svc_url()->str:
        return SAC.get_str('ucasal.endpoint.qr.url')         

    @staticmethod
    def stamps_svc_url()->str:
        return SAC.get_str('ucasal.endpoint.stamps.url')    

    @staticmethod
    def change_acta_svc_url()->str:
        return SAC.get_str('ucasal.endpoint.change_acta.url')      

    @staticmethod
    def shorten_url_svc_url()->str:
        return SAC.get_str('ucasal.endpoint.acortar_url.url')    

    @staticmethod
    def shorten_url_svc_env()->str:
        return SAC.get_str('ucasal.endpoint.acortar_url.env')

    @staticmethod
    def acta_validation_url_template()->str:
        return SAC.get_str('ucasal.acta.validation_url_template')
    
    @staticmethod
    def otp_validation_url_template()->str:
        return SAC.get_str('ucasal.endopint.otp.validation_url_template')
    
    @staticmethod
    def titulo_validation_url_template()->str:
        env = SAC.get_str('ucasal.endpoint.acortar_url.env', default='produccion')
        if env == 'desarrollo':
            return SAC.get_str('ucasal.titulo.validation_url_template', 
                             default='https://www.ucasal.edu.ar/validar/index.php?d=titulo&e=testing&uuid={{uuid}}')
        else:
            return SAC.get_str('ucasal.titulo.validation_url_template',
                             default='https://www.ucasal.edu.ar/validar/index.php?d=titulo&uuid={{uuid}}')
    
    @staticmethod
    def base_url()->str:
        # URL base del sistema para callbacks
        try:
            return SAC.get_str('ucasal.base_url', default='https://ucasal-uat.athento.com')
        except:
            return 'https://ucasal-uat.athento.com'

def default_permissions(func):
    @api_view(['POST', 'GET', 'DELETE', 'PUT', 'OPTIONS'])
    @authentication_classes([])
    @permission_classes([])
    def f(*args, **kargs):
        return func(*args, **kargs)
    return f

def getJsonBody(request):
    try:
        return decodeJSON(request.data) if type(request.data) != dict else request.data
    except Exception as e:
        raise AthentoseError('Error parseando el request body JSON string:\r\n' + traceback.format_exc())
    
def getJsonOrStr(something):
    try:
        return decodeJSON(something) if type(something) != dict else str(something)
    except Exception as e:
        return str(something)
    
def decodeUTF8(bite_string, code='utf-8'):
    return bite_string.decode(code)


def traceback_ret(func):
    def f(request, *args, **kargs):
        try:
            return func(request, *args, **kargs)
        except Exception:
            content = encodeJSON({
                'request': {
                    'method': request.method,
                    'meta': {k: v for k, v in request.META.items() if type(v) in serializableJsonTypes},
                    'params': {k: v for k, v in request.GET.items()} if request.method == 'GET' else {},
                    'body': getJsonOrStr(request.data)
                },
                'functionParams': {
                    'args': [a if type(a) in serializableJsonTypes else str(a) for a in args],
                    'kargs': {k: v if type(v) in serializableJsonTypes else str(v) for k, v in kargs.items()}
                },
                'error': traceback.format_exc()
            })

            logger = SpLogger("athentose", "traceback_ret")
            logger.error(content)
            return HttpResponse(
                content=content,
                content_type='application/json',
                status=500
            )
    return f    

def get_totp_key(key):
    return _totp_base_key + '|' + key

def dumper(obj):
    try:
        return obj.toJSON()
    except:
        try:
            return obj.__dict__
        except:
            return str(obj)


