from model import File
import io
import requests
from core.exceptions import AthentoseError
from ucasal.mocks.sp_logger import SpLogger
from base64 import b64encode
from ucasal.utils import UcasalConfig
from model.exceptions.invalid_otp_error import InvalidOtpError
class UcasalServices:
    logger = SpLogger("athentose", "UcasalServices")

    #TODO: setear "VERIFY_CERTIFICATE = True" cuando quede productivo 
    VERIFY_CERTIFICATE = False
    
    @classmethod
    def get_auth_token(cls, user:str, password:str)->str:
        logger = cls.logger
        logger.entry()
        endpoint = UcasalConfig.token_svc_url()
        data = f'usuario={user}&clave={password}'
        
        headers ={'Content-Type': 'application/x-www-form-urlencoded'}  
        logger.debug("Llamando a requests.post con estos parámetros: %s" % str({'url':endpoint, 'data': data, 'headers':headers}))

        response = requests.post(url=endpoint, data=data, headers=headers)

        if response.status_code == requests.codes.ok:
            return logger.exit(response.text.strip())
        else:
            raise logger.exit(AthentoseError('Error inesperado obteniento token de autenticación: ' + response.reason), exc_info=True)  
            
    @classmethod
    def get_qr_image(cls, url:str)->io.BytesIO:
        logger = cls.logger
        logger.entry()
        
        # En modo mock, devolver una imagen QR simple
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return logger.exit(img_bytes.getvalue())
        except ImportError:
            # Si no está instalado qrcode, devolver una imagen simple
            logger.debug("qrcode no instalado, devolviendo imagen mock")
            return logger.exit(b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")   
    
    @classmethod
    def get_short_url(cls, auth_token:str, url:str)->str:
        #TODO: consultar servicio de UCASAL
        logger = cls.logger
        logger.entry()
        endpoint = UcasalConfig.shorten_url_svc_url()
        headers = {'Authorization': f'Bearer {auth_token}'}
        json = {
          'url': url,
          'entorno': UcasalConfig.shorten_url_svc_env() if UcasalConfig.shorten_url_svc_env() else 'produccion'
        }

        logger.debug("Llamando a requests.post con estos parámetros: %s" % str({'url':endpoint, 'json': json, 'headers':headers}))
        response = requests.post(url=endpoint, headers=headers, json=json, verify=cls.VERIFY_CERTIFICATE)

        logger.debug(f'response.status_code: {response.status_code}')
        logger.debug(f'response.status_code type: { type(response.status_code)}')
        logger.debug(f'requests.codes.ok: {requests.codes.ok}')
        logger.debug(f'requests.codes.ok type: {type(requests.codes.ok)}')
        logger.debug(f'response.text: {response.text}')
        logger.debug(f'response.json(): {response.json()}')

        if response.status_code in [200, 201]:
            return logger.exit(response.json()['url_corta'])
        else:
            raise logger.exit(AthentoseError('Error inesperado obteniendo url corta: ' + response.reason), exc_info=True)   


    @classmethod
    def register_in_blockchain(cls, auth_token:str, hash:str, file_uuid:str, callback_url:str)->str:
        #import logging
        #nlogger = logging.getLogger("athentose")

        #nlogger.debug("nlogger - Enter register_in_blockchain")


        logger = cls.logger
        logger.entry()
        #TODO: validar parámetros
                
        endpoint = UcasalConfig.stamps_svc_url()
        headers = {'Authorization': f'Bearer {auth_token}'}
        #TODO: y el file_uuid, no se envía?
        data = {
            'fileHash': hash,
            'callbackUrl': callback_url
        }


        request_info = str({'url':endpoint, 'json':data, 'headers':headers})
        
        logger.debug(f"Llamando a requests.post con estos parametros: {request_info}")
        logger.debug(f"Llamando a requests.post con estos parámetros: {request_info}")

        response = requests.post(url=endpoint, json=data, headers=headers)

        rta = str(response.text)
        logger.debug(f"Respuesta del servicio: {rta}")

        if response.status_code == requests.codes.ok:
            return logger.exit(response.text)
            #TODO: Manejar response?
        else:
            raise logger.exit(AthentoseError('Error inesperado registrando el hash en UCASAL/BFA: ' + response.reason), exc_info=True) 

    @classmethod
    def notify_rejection(cls, auth_token:str, uuid:str, previous_uuid:str, reason:str)->str:
        logger = cls.logger
        logger.entry()
        endpoint = f'{UcasalConfig.change_acta_svc_url()}/{uuid}'
        headers = {'Authorization': f'Bearer {auth_token}'}
        data = {'estado': 1, 'motivo': reason, 'previous_uuid': previous_uuid}
        
        logger.debug("Llamando a requests.patch con estos parámetros: %s" % str({'url':endpoint, 'headers':headers,  'json':data}))
        response = requests.patch(url=endpoint, headers=headers, json=data)

        if response.status_code == requests.codes.ok:
            return logger.exit(response.text)
        else:
            raise logger.exit(AthentoseError('Error inesperado notificando rechazo del acta: ' + response.reason), exc_info=True)   

    @classmethod
    def notify_blockchain_success(cls, auth_token:str, uuid:str)->str:
        logger = cls.logger
        logger.entry()
        endpoint = f'{UcasalConfig.change_acta_svc_url()}/{uuid}'
        headers = {'Authorization': f'Bearer {auth_token}'}
        data = {'estado': 5}
        
        logger.debug("Llamando a requests.patch con estos parámetros: %s" % str({'url':endpoint, 'headers':headers,  'json':data}))
        response = requests.patch(url=endpoint, headers=headers, json={'estado': 5})

        if response.status_code == requests.codes.ok:
            return logger.exit(response.text)
        else:
            raise logger.exit(AthentoseError('Error inesperado notificando éxito registrando el acta en blockchain: ' + response.reason), exc_info=True)   
    
    @classmethod
    def validate_otp(cls, user:str, otp:int):
        logger = cls.logger
        logger.entry()
        endpoint = UcasalConfig.otp_validation_url_template().format(usuario=user, token=otp)
        headers = {}
        
        logger.debug("Llamando a requests.get con estos parámetros: %s" % str({'url':endpoint, 'headers':headers}))
        response = requests.get(url=endpoint, headers=headers)

        if response.status_code == requests.codes.ok:
            return logger.exit() #OK
        if response.status_code == requests.codes.unauthorized:
            raise logger.exit(InvalidOtpError('El código OTP es inválido o ha expirado.'))
        else:
            raise logger.exit(AthentoseError(f'Error inesperado validadando el código OTP: HTTP code: {response.status_code}. HTTP body {response.text}'), exc_info=True)   
        