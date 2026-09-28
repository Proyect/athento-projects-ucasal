from file.models import File
import requests
from core.exceptions import AthentoseError
from custom.sp_libs.python.sp_logger.sp_logger import SpLogger
from ucasal2.utils import UcasalConfig
from ucasal2.model.ucasal.exceptions import UcasalServiceError

class TitulosServices:
    @classmethod    
    def notify_blockchain_success(cls, uuid: str, state: int, auth_token: str) -> str:
        logger = SpLogger.getLogger("athentose")
        logger.entry()        

        try:
            base = UcasalConfig.change_designaciones_svc_url().rstrip('/')
            endpoint = f"{base}/{uuid}"

            data = {"estado": state}
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            logger.debug(f"[Designaciones] PATCH {endpoint} con payload={data}")
            resp = requests.patch(url=endpoint, json=data, headers=headers)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.error(f"[Designaciones] Error notificando a UCASAL estado={state} para uuid={uuid}: {e}")
            raise

      
    @classmethod
    def set_callback_url(cls, uuid: str) -> str:
        base = UcasalConfig.titulo_bfaresponse_endpoint()
        return f"{base}/f8f29864-0cbe-4217-8fda-03045b0eaf97/bfaresponse"
    

    @classmethod
    def change_state_integration(cls, uuid: str, state: int, auth_token: str):
        """
        Notifica al backend UCASAL el cambio de estado de una Designación.
        Usa PATCH con Authorization Bearer, contra el endpoint configurado en
        ucasal2.endpoint.change_designaciones.url
        """
        logger = SpLogger.getLogger("athentose")
        logger.entry()

        try:
            base = UcasalConfig.change_designaciones_svc_url().rstrip('/')
            endpoint = f"{base}/{uuid}"

            data = {"estado": state}
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            logger.debug(f"[Designaciones] PATCH {endpoint} con payload={data}")
            resp = requests.patch(url=endpoint, json=data, headers=headers)

            logger.debug(f"[Designaciones] Respuesta UCASAL ({resp.status_code}): {resp.text}")
            resp.raise_for_status()

            return resp

        except Exception as e:
            logger.error(f"[Designaciones] Error notificando estado {state} para {uuid}: {str(e)}")
            raise

    @classmethod
    def register_in_blockchain(cls, auth_token:str, hash:str, file_uuid:str, callback_url:str)->str: #firma_programas
        import logging
        nlogger = logging.getLogger("athentose")

        nlogger.debug("nlogger - Enter register_in_blockchain")
     
        
        endpoint = UcasalConfig.stamps_svc_url()
        headers = {'Authorization': f'Bearer {auth_token}'}
        
        data = {
            'fileHash': hash,
            'callbackUrl': callback_url
        }


        request_info = str({'url':endpoint, 'json':data, 'headers':headers})
        
        nlogger.debug(f"Llamando a requests.post con estos parametros: {request_info}")
        
        response = requests.post(url=endpoint, json=data, headers=headers)

        rta = str(response.text)
        nlogger.debug(f"Respuesta del servicio: {rta}")

        if response.status_code == requests.codes.ok:
            return nlogger.exit(response.text)
            #TODO: Manejar response?
        else:
            raise nlogger.exit(AthentoseError('Error inesperado registrando el hash en UCASAL/BFA: ' + response.reason), exc_info=True) 

