from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
#from core.exceptions import AthentoseError
from json import loads as decodeJSON, dumps as encodeJSON
import traceback
try:
    from sp_athento_config import SpAthentoConfig as SAC
except ImportError:
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


class ActaStates:
    recibida = 'Recibida'
    pendiente_otp = 'Pendiente Firma OTP'
    pendiente_blockchain = 'Pendiente Blockchain'
    firmada = 'Firmada'
    fallo_blockchain = 'Fallo en Blockchain'
    rechazada = 'Rechazada'

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


