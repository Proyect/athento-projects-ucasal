from django.urls import re_path as url
from ucasal.utils import default_permissions, traceback_ret, encodeJSON, getJsonBody, decodeUTF8
from ucasal.utils import METHOD_NOT_ALLOWED
from ucasal.utils import ActaStates 
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger
try:
    from ucasal.mocks.sp_totp_generator import TOTPGenerator
except ImportError:
    from ucasal.mocks.sp_totp_generator import TOTPGenerator
try:
    from ucasal.mocks.sp_form_totp_notifier import SpFormTotpNotifier
except ImportError:
    from ucasal.mocks.sp_form_totp_notifier import SpFormTotpNotifier
try:
    from ucasal.mocks.sp_athento_config import SpAthentoConfig as AC
except ImportError:
    from ucasal.mocks.sp_athento_config import SpAthentoConfig as AC
from ucasal.utils import UcasalConfig
from ucasal.utils import get_totp_key
from django.http import HttpResponse
from model import File
from core.exceptions import AthentoseError
from django.core.files import File as FileObject
try:
    from ucasal.mocks.sp_pdf_otp_simple_signer import SpPdfSimpleSigner, QRInfo, OTPInfo
except ImportError:
    from ucasal.mocks.sp_pdf_otp_simple_signer import SpPdfSimpleSigner, QRInfo, OTPInfo
from external_services.ucasal.ucasal_services import UcasalServices
from ucasal.utils import uuid_previo_metadata_name
from model.exceptions.invalid_otp_error import InvalidOtpError

from datetime import datetime
import pytz
from tempfile import NamedTemporaryFile
from django.conf import settings
import hashlib
from posixpath import join as urljoin
import os

""""

@default_permissions
def entrypoint(request, *args, **kargs):
    method = request.method
    if method == 'GET':
        return get(request, *args, **kargs)
    elif method == 'PUT':
        return put(request, *args, **kargs)
    else:
        return METHOD_NOT_ALLOWED
"""


'''
Envía una correo con código OTP a un usuario, válido sólo para un formulario específico
Devuelve el siguiente diccionario: 
    {
        'send_to': 'correo del destinatario',
        'otp': 'código OTP',
        'expiration': fecha y tiempo de expiración en segundos desde epoch
    }    
'''

@default_permissions
@traceback_ret
## Envía OTP al docente por correo electrónico
## Este endpoint no se usa más, ya que el docente obtiene el OTP desde su app de autenticación
def sendotp(request, uuid):
    logger = SpLogger("athentose", "actas.sendotp")
    logger.entry()
    if request.method != 'POST':
        return  logger.exit(METHOD_NOT_ALLOWED)      

    #TODO: validar que uuid sea de un doctype acta
   
    notification_template_name = 'ucasal_custom_otp_notification'
    send_to = 'metadata.acta_docente_asignado'

    info = SpFormTotpNotifier.send_otp_notification(
        uuid=uuid, 
        send_to=send_to,
        notification_template_name=notification_template_name,
        otp_validity_seconds = UcasalConfig.otp_validity_seconds()
    )
    
    return logger.exit(HttpResponse(encodeJSON({
      'sent_to': info['send_to'],    
      #'otp': info['otp'],
      'expiration': info['expiration'] 
      }), 
      content_type="application/json"
    ))

# ucasal_qr_673c253a-d851-4c10-9f85-69ca3e3bd39a.png
@default_permissions
@traceback_ret
def qr(request):
    from django.http import HttpResponse
    logger = SpLogger("athentose", "actas.qr")
    logger.entry()    
    
    body = getJsonBody(request)

    if request.method != 'GET':
        return  logger.exit(METHOD_NOT_ALLOWED)      

    bytes = UcasalServices.get_qr_image(url=body['url'])

    return HttpResponse(
        bytes,
        content_type="image/png" 
    )
    #return FileResponse(open("/var/www/athentose/media/tmp/ucasal_qr_673c253a-d851-4c10-9f85-69ca3e3bd39a.png", "rb"))

@default_permissions
@traceback_ret
def getconfig(request):
    from django.http import HttpResponse
    from config.utils import get_config

    logger = SpLogger("athentose", "actas.getconfig")
    logger.entry()    
        
    if request.method != 'GET':
        return  logger.exit(METHOD_NOT_ALLOWED)      

    body = getJsonBody(request)
    key = body['key']
    is_secret = body.get('is_secret', False)

    logger.debug("", additional_info={'key': key , 'is_secret': is_secret})

    config_value = AC.get_str(key, is_secret=is_secret)

    logger.debug(f'config_value: {str(config_value)}')
    
    return logger.exit(HttpResponse(
        config_value,
        content_type="text/plain" 
    ))


@default_permissions
@traceback_ret
def bfaresponse(request, uuid):
    try:    
        fil:File = None
        logger = SpLogger("ucasal", "actas.bfaresponse")
        logger.entry()

        if request.method != 'POST':
            return  logger.exit(METHOD_NOT_ALLOWED)
        
        body = getJsonBody(request)

        ## Validaciones

        # Validar 'status' del body
        result = body.get('status')
        if result not in ['success', 'failure']:
            raise AthentoseError(f"'status' debe ser 'success' o 'failure' en lugar de {result}")
    
        
        # Validar existencia y doctype del UUID recibido
        fil = _get_acta(uuid)
        if not fil:
            raise FileNotFoundError(f"El acta '{uuid}' no existe")
        
        if not fil.doctype.name == 'acta':
            raise AthentoseError(f"El documento con uuid '{uuid}' es de tipo '{fil.doctype.label}' en lugar de 'Acta'")

        # Verificar estados válidos del acta
        lifecycle_state = fil.life_cycle_state.name
        valid_states = [ActaStates.pendiente_blockchain, ActaStates.fallo_blockchain]
        if not lifecycle_state in valid_states:
            raise AthentoseError(f"Sólo se puede registrar el resultado de blockchain si el acta encuentra en los estados {' o '.join(valid_states)}, pero el estado actual es '{lifecycle_state}'.")


        # Guardar fecha de firma
        tz = pytz.timezone('America/Argentina/Buenos_Aires')
        date_str = datetime.now(tz=tz).strftime('%Y-%m-%d')    
            
        fil.set_metadata('metadata.acta_fecha_firma', date_str, overwrite=True)

        ## Registrar el sello como feature (tanto por éxito como error en BFA)
        # Setear el feature
        fil.set_feature('bfa.result', encodeJSON(body))
        
        # Cambiar ciclo de vida 
        if result == 'success':
            # Notificar a UCASAL el registro exitoso en blockchain
            auth_token = UcasalServices.get_auth_token(user=UcasalConfig.token_svc_user(), password = UcasalConfig.token_svc_password())
            UcasalServices.notify_blockchain_success(auth_token=auth_token, uuid=fil.uuid)
            
            #TODO: ¿validar que el sello corresponda al hash?
            #TODO: ¿validar que el sello no haya sido previamente registrado el sello?
            #fil.set_metadata('metadata.acta_resultado_bfa', 'exitoso', overwrite=True)
            fil.change_life_cycle_state(ActaStates.firmada) #, force_transition=True)
        else:
            #TODO: ¿qué hacemos en caso de falla?
            #fil.set_metadata('metadata.acta_resultado_bfa', 'fallido', overwrite=True)
            fil.change_life_cycle_state(ActaStates.fallo_blockchain) #, force_transition=True)

        fil.set_feature('registro.en.blockchain', result)

        return logger.exit(HttpResponse(
            'Resultado BFA guardado exitosamente'
        ))
    except FileNotFoundError as e:
        _save_bfaresponse_error_to_feature(fil)
        return logger.exit(HttpResponse(
            str(e), 
            status='404'
        ), exc_info=True)
    except AthentoseError as e:
        _save_bfaresponse_error_to_feature(fil)
        return logger.exit(HttpResponse(
            str(e), 
            status='400'
        ), exc_info=True)
    
    except Exception as e:
        _save_bfaresponse_error_to_feature(fil)
        raise logger.exit(HttpResponse(
            str(e), 
            status='500'
        ), exc_info=True)

@default_permissions
@traceback_ret
## Valida el OTP ingresado por el docente, firma el PDF y envía el hash a BFA 
#  (por medio del endpoint de UACASAL)
def registerotp(request, uuid):    
    try:
        logger = SpLogger("athentose", "actas.registerotp")
        logger.entry()

        if request.method != 'POST':
            return  logger.exit(METHOD_NOT_ALLOWED)          
        
        body = getJsonBody(request)

        ## Obtener acta
        fil = _get_acta(uuid)
        if not fil:
            raise FileNotFoundError(f'El acta {uuid} no existe')

        if not fil.doctype.name == 'acta':
            raise AthentoseError(f"El documento con uuid '{uuid}' es de tipo '{fil.doctype.label}' en lugar de 'Acta'")

        # Verificar estados válidos del acta
        lifecycle_state = fil.life_cycle_state.name
        signature_valid_states = [ActaStates.pendiente_otp, ActaStates.fallo_blockchain]
        if not lifecycle_state in signature_valid_states :
            raise AthentoseError(f"Sólo se puede firmar el acta si se encuentra en los estados {' o '.join(signature_valid_states)}, pero el estado actual es '{lifecycle_state}'.")

        ## Validar parámetros
        #TODO: mejorar en gral la validacion de formato de todos los parámetros
        # Validar OTP 
        otp = str(body.get('otp', ''))
        if(not _is_digit(otp)):
            raise AthentoseError(f"'otp' debe ser un número entero positivo en lugar de '{otp}'")
        
        otp = int(otp)

        # Validar OTP
        #totp_gen = TOTPGenerator(key = get_totp_key(uuid), token_validity_seconds=UcasalConfig.otp_validity_seconds())
        #totp_gen.verify_token(otp, 0 )
        #if totp_gen.verified == False:
        #    raise AthentoseError('El código es OTP inválido o ha expirado')
        mail_docente = fil.gmv('metadata.acta_docente_asignado')

        if(not _is_non_empty_string(mail_docente)):
            raise AthentoseError(f"El mail del docente debe ser un string no vacío en lugar de '{mail_docente}'")
        
        UcasalServices.validate_otp(user=mail_docente, otp=otp)

        # Obtener token de autenticación de UCASAL
        auth_token = UcasalServices.get_auth_token(user=UcasalConfig.token_svc_user(), password = UcasalConfig.token_svc_password())

        # Verificar si el documento ya fue firmado con OTP
        firmada_con_opt = fil.gfv('firmada.con.OTP')
        # Validar IP
        if not firmada_con_opt == "1":
            logger.debug('Firmando acta con OTP...')
            ip = body.get('ip')
            if(not isinstance(ip, str) or len(ip.strip())==0):
                raise AthentoseError("'ip' debe ser un string no vacío")

            # Validar latitude
            latitude = body.get('latitude')
            if not isinstance(latitude, (int, float)):
                raise AthentoseError("'latitude' debe ser un entero o un float")

            # Validar longitude
            longitude = body.get('longitude')
            if not isinstance(longitude, (int, float)):
                raise AthentoseError("'longitude' debe ser un entero o un float")
            
            # Validar accuracy
            accuracy = body.get('accuracy')
            if(not isinstance(accuracy, str) or len(accuracy.strip())==0):
                raise AthentoseError("'accuracy' debe ser un string no vacío")     

            # Validar user_agent
            user_agent = body.get('user_agent')
            if not isinstance(user_agent, str) or len(user_agent.strip())==0:
                raise AthentoseError("'user_agent' debe ser un string no vacío")

            ## Agregar QR e info de OTP al PDF
            # Obtener QR image
            url_to_shorten = UcasalConfig.acta_validation_url_template().replace('{{uuid}}', str(fil.uuid))
            short_url = UcasalServices.get_short_url(auth_token=auth_token, url=url_to_shorten)
            qr_stream = UcasalServices.get_qr_image(url=short_url)
            #TODO: confirmar extensión del qr
            qr_image_tmp_path = f'/var/www/athentose/media/tmp/ucasal_qr_{fil.uuid}.png'
            with open(qr_image_tmp_path, 'wb') as qr_file:
                qr_file.write(qr_stream)

            # Generar QR info
            nombre_docente = fil.gmv('metadata.acta_nombre_docente_asignado')
            mail_docente_ofuscado = _get_mail_for_otp(mail_docente)
            fecha_firma = _get_arg_time()
            qr_text = f"Firmado con OTP por:\r\n{nombre_docente}\r\n{mail_docente_ofuscado}\r\n{fecha_firma}"
            qr_info = QRInfo(
                image_path=qr_image_tmp_path,
                image_text=qr_text,
                x=10, y=10, width=40, height=40
            )
            logger.debug(f'QR info: {qr_info}')

            # Generar OTP info
            otp_info = OTPInfo(mail=mail_docente_ofuscado, ip=ip, latitude=latitude, longitude=longitude, accuracy=accuracy, user_agent=user_agent)
            logger.debug(f'OTP info: {otp_info}')

            # Incrustar QR y OTP en el pdf
            signer = SpPdfSimpleSigner()
            pdf_out_stream = signer.sign(input_pdf_path=fil.file.path, qr_info=qr_info, otp_info=otp_info)

            # Borrar la imagen temporal del QR
            _delete_file(qr_image_tmp_path)        

            # actualizar binario del acta
            with NamedTemporaryFile(dir=settings.MEDIA_TMP, suffix='.ucasal.tmp') as pdf_temp:
                pdf_temp.write(pdf_out_stream.getbuffer())
                fil.update_binary(FileObject(pdf_temp), fil.filename + ".pdf")
                fil.set_feature('firmada.con.OTP', "1")

            logger.debug('Acta firmada con OTP exitosamente')    
        else:
            logger.debug('El acta ya estaba firmada con OTP. Salteamos este paso y vamos a registrar en Blockchain')

        ## #TODO: Enviar PDF a sellar con BFA (por medio de un servicio de UCASAL no disponible aún)
        # Verficar si no fue enviada previamente
        registrada_en_blockchain = fil.gfv('registro.en.blockchain')

        if(registrada_en_blockchain == 'pending'):
            raise AthentoseError('El acta ya había sido enviada a blockchain y su resultado aún está pendiente')

        if(registrada_en_blockchain == 'success'):
            raise AthentoseError('El acta está registrada en blockchain')

        # Calcular el hash del PDF
        pdf_hash = _get_pdf_hash(fil)
        callback_url = urljoin(request.build_absolute_uri('/'), 'ucasal/api/actas/', str(fil.uuid), 'bfaresponse')
        ok_response_text = UcasalServices.register_in_blockchain(auth_token=auth_token, hash=pdf_hash, file_uuid=str(fil.uuid), callback_url=callback_url)
        fil.set_feature('ucasal.svc.ok_response', ok_response_text)
        # Cambiar estado a Pendiente Blockchain
        #TODO: forzar transición?
        fil.change_life_cycle_state(ActaStates.pendiente_blockchain) #, force_transition=True)
        fil.set_feature('registro.en.blockchain', 'pending')

        return logger.exit(HttpResponse(
            encodeJSON({
                'otp_is_valid': True,
                'callback_url': callback_url
            }), 
            content_type="application/json"
        ))            
    except FileNotFoundError as e:
        return logger.exit(HttpResponse(
            str(e), 
            status='404'
        ), exc_info=True)        
    except AthentoseError as e:
        return logger.exit(HttpResponse(
            str(e), 
            status='400'
        ), exc_info=True)
    except InvalidOtpError as e:
        return logger.exit(HttpResponse(
            str(e), 
            status='400'
        ), exc_info=True)
    except Exception as e:
        return logger.exit(HttpResponse(
            str(e), 
            status='500'
        ), exc_info=True)

@default_permissions
@traceback_ret
## Rechaza el acta de parte del docente
def reject(request, uuid):    
    try:
        
        logger = SpLogger("athentose", "actas.reject")
        logger.entry()

        if request.method != 'POST':
            return  logger.exit(METHOD_NOT_ALLOWED)          
        
        body = getJsonBody(request)

        ## Obtener acta
        fil = _get_acta(uuid)
        if not fil:
            raise AthentoseError(f'El acta {uuid} no existe')

        if not fil.doctype.name == 'acta':
            raise AthentoseError(f"El documento con uuid '{uuid}' es de tipo '{fil.doctype.label}' en lugar de 'Acta'")

        ## Validar parámetros
        #TODO: mejorar en gral la validacion de formato de todos los parámetros
        # Validar motivo 
        motivo = str(body.get('motivo', ''))
        if(len(motivo.strip())==0):
            raise AthentoseError(f"'motivo' debe ser un string no vacío en lugar de '{motivo}'")
        
        #TODO: Tal vez convenga validar con OTP
        #totp_gen = TOTPGenerator(key = get_totp_key(uuid), token_validity_seconds=otp_validity_seconds)
        #totp_gen.verify_token(otp, 0 )
        
        #if totp_gen.verified == False:
        #    raise AthentoseError('El código es OTP inválido o ha expirado')
        
        # Verificar si el acta aún está pendiente de firma
        lifecycle_state = fil.life_cycle_state.name
        if lifecycle_state != ActaStates.pendiente_otp:
            raise AthentoseError(f"Sólo se puede rechazar el acta en estado '{ActaStates.pendiente_otp}', pero el estado actual es '{lifecycle_state}'.")

        # Verificar si el documento ya fue firmado con OTP
        firmada_con_opt = fil.gfv('firmada.con.OTP')
        if firmada_con_opt == "1":
            raise AthentoseError(f"El acta ya fue firmada y no puede ser rechazada.")

        ## Registrar el rechazo del acta

        # Guardar fecha de rechazo
        #tz = pytz.timezone('America/Argentina/Buenos_Aires')
        #date_str = datetime.now(tz=tz).strftime('%Y-%m-%d')        
        #fil.set_metadata('metadata.acta_fecha_rechazo', date_str, overwrite=True)

        # Guardar el motivo de rechazo
        #fil.set_metadata('metadata.acta_motivo_rechazo', motivo, overwrite=True)

        # Notificar a UCASAL para que puedan editar el acta
        auth_token = UcasalServices.get_auth_token(user=UcasalConfig.token_svc_user(), password = UcasalConfig.token_svc_password())
        uuid_acta_previa = str(fil.gmv(uuid_previo_metadata_name)).replace('None', '')
        UcasalServices.notify_rejection(auth_token=auth_token, uuid=fil.uuid, previous_uuid = uuid_acta_previa, reason=motivo)

        # Cambiar estado a Rechazada (aunque la borremos luego, si hay error invocando a UCASAL, al menos que rechazada en Athento)
        #TODO: forzar transición?
        fil.change_life_cycle_state(ActaStates.rechazada) #, force_transition=True)
        
        # Borrar el acta
        fil.removed = True
        fil.save()

        # Mover el acta al espacio Papelera
        #fil.move_to_serie(name='papelera')

        return logger.exit(HttpResponse('Acta rechazada exitosamente'))            
      
    except AthentoseError as e:
        return logger.exit(HttpResponse(
            str(e), 
            status='400'
        ), exc_info=True)
    except Exception as e:
        raise logger.exit(e, exc_info=True)


def _get_pdf_hash(fil):
    path = fil.file.path
    byte_content = None
    with open(path, mode='rb') as f:
        byte_content = f.read()
    return hashlib.sha256(byte_content).hexdigest()

def _get_acta(uuid:str):
    try:
        return File.objects.get(uuid=uuid) 
    except File.DoesNotExist:
        return None
    
def _get_arg_time():
    argentina_timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    current_time = datetime.now(argentina_timezone)
    formatted_time = current_time.strftime('%d/%m/%Y %H:%M:%S')    

    return formatted_time

def _get_mail_for_otp(mail):
    mail_user, mail_domain = mail.split('@')
    n = len(mail_user) // 2
    obfuscated_mail = mail_user[0:n] + ('*' * n) + '@' + mail_domain

    return obfuscated_mail

def _delete_file(file_path:str):
    logger = SpLogger("athentose", "actas._delete_file")
    logger.entry()    
    try:
      if os.path.isfile(file_path):
          os.remove(file_path)    
          logger.exit(f"File '{file_path}' removed.")    
      else:
          logger.exit(f"File '{file_path}' was not removed because it does not exist.")    
    except Exception as e:
        logger.exit(e, exc_info=True)

def _is_non_empty_string(value:str):
    return isinstance(value, str) and value.strip() != ""

def _is_digit(value:str):
    return isinstance(value, str) and  value.isdigit() 


routes = [
    url(r'^actas/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/registerotp\/{0,1}$', registerotp),
    url(r'^actas/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/sendotp\/{0,1}$', sendotp),
    url(r'^actas/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/bfaresponse\/{0,1}$', bfaresponse),
    url(r'^actas/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/reject\/{0,1}$', reject),
    url(r'^actas/qr/{0,1}$', qr),
    url(r'^actas/getconfig/{0,1}$', getconfig), #Comentar por seguridad
]

def _save_bfaresponse_error_to_feature(fil:File):
    import traceback as tb
    if fil:
        fil.set_feature('svc.bfaresponse.error',tb.format_exc())
        #TODO: guardar la fecha