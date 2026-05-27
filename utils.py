from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from core.exceptions import AthentoseError
from json import loads as decodeJSON, dumps as encodeJSON
import traceback
import requests
from custom.sp_libs.sp_athento.sp_athento_config import SpAthentoConfig as SAC
from custom.sp_libs.python.sp_logger.sp_logger import SpLogger
from datetime import datetime
import pytz
import hashlib


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

# Nombres de campos Resoluciones
class CamposEquivalencias :
    codigo_sector_equivalencias = 'metadata.resolucion_equivalencia_codigo_sector'

# Nombre del doctype del Acta
acta_examen_doctype_name = 'acta'

# Nombres de Estados de Ciclo de Vida Designaciones
class DesignacionesStates:
    pendiente_validacion_ld = 'Pendiente de Validacion LD'
    pendiente_validacion_personal = 'Pendiente de Validacion Personal'
    pendiente_validacion_rrhh = 'Pendiente de Validacion RRHH'
    pendiente_firma_otp = 'Pendiente de Firma OTP'
    pendiente_blockchain = 'Pendiente de Blockchain'
    fallo_blockchain = 'Fallo en Blockchain'
    firmado = 'Firmado'
    rechazado = 'Rechazado'

# Nombres de Estados de Ciclo de Vida Equivalencia
class EquivalenciaStates:
    recibida = 'Recibida'
    pendiente_DA = 'Pendiente de Revisión (DA)'
    pendiente_firma = 'Pendiente Firma OTP'
    pendiente_blockchain = 'Pendiente de Blockchain'
    fallo_blockchain = 'Fallo en Blockchain'
    firmada = 'Firmada'
    rechazada = 'Rechazada'

class ActaStates:
    recibida = 'Recibida'
    pendiente_otp = 'Pendiente Firma OTP'
    pendiente_blockchain = 'Pendiente Blockchain'
    firmada = 'Firmada'
    fallo_blockchain = 'Fallo en Blockchain'
    rechazada = 'Rechazada'

class TituloStates:
    pendiente_validacion_da = 'Pendiente de validacion DA (direccion de alumnos)'
    pendiente_validacion_fd = 'Pendiente de validacion FD (firma del decano)'
    pendiente_validacion_fr = 'Pendiente de validacion FR (firma del rector)'
    pendiente_validacion_tit = 'Pendiente de Validacion TIT (titulo)'
    pendiente_validacion_fsg = 'Pendiente de validacion FSG (secretaria general)'
    pendiente_firma_otp = 'Pendiente de Firma OTP'
    pendiente_blockchain = 'Pendiente Blockchain'
    fallo_blockchain = 'Fallo en Blockchain'
    firmado = 'Firmado'
    rechazado = 'RECHAZADO'

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
    def qr_svc_param_verify()->bool:
        return SAC.get_bool('ucasal.endpoint.qr.param.verify')         

    @staticmethod
    def stamps_svc_url()->str:
        return SAC.get_str('ucasal.endpoint.stamps.url')    

    @staticmethod
    def change_acta_svc_url()->str:
        return SAC.get_str('ucasal.endpoint.change_acta.url')
    
    @staticmethod
    def change_equivalencia_svc_url()->str:
        return SAC.get_str('ucasal.endpoint.change_equivalencia.url')
    
    @staticmethod
    def change_designaciones_svc_url()->str:
        return SAC.get_str('ucasal.endpoint.change_designaciones.url')

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
    def equivalencia_validation_url_template()->str:
        return SAC.get_str('ucasal.equivalencia.validation_url_template')
    
    @staticmethod
    def equivalencia_bfaresponse_endpoint()->str:
        return SAC.get_str('ucasal.equivalencia.bfaresponse_endpoint')
    
    @staticmethod
    def equivalencia_nro_resolucion_endpoint()->str:
        return SAC.get_str('ucasal.equivalencia.nro_resolucion_endpoint')
    
    @staticmethod
    def designaciones_bfaresponse_endpoint()->str:
        return SAC.get_str('ucasal.designaciones.bfaresponse_endpoint')
    
    @staticmethod
    def designaciones_validation_url_template()->str:
        return SAC.get_str('ucasal.designaciones.validation_url_template')

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

def is_digit(value:str):
    return isinstance(value, str) and  value.isdigit()

def is_non_empty_string(value:str):
    return isinstance(value, str) and value.strip() != ""

def get_mail_for_otp(mail):
    mail_user, mail_domain = mail.split('@')
    n = len(mail_user) // 2
    obfuscated_mail = mail_user[0:n] + ('*' * n) + '@' + mail_domain

    return obfuscated_mail

def get_arg_time():
    argentina_timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    current_time = datetime.now(argentina_timezone)
    formatted_time = current_time.strftime('%d/%m/%Y %H:%M:%S')    

    return formatted_time

def get_pdf_hash(fil):
    path = fil.file.path
    byte_content = None
    with open(path, mode='rb') as f:
        byte_content = f.read()
    return hashlib.sha256(byte_content).hexdigest()



def dumper(obj):
    try:
        return obj.toJSON()
    except:
        try:
            return obj.__dict__
        except:
            return str(obj)


