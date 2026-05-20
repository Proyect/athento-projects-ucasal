from file.models import File
import requests
from core.exceptions import AthentoseError
from custom.sp_libs.python.sp_logger.sp_logger import SpLogger
from utils import UcasalConfig
from model.ucasal.exceptions import UcasalServiceError

class DesignacionesServices:
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
    def set_callback_url(cls, uuid:str)->str:
        logger = SpLogger.getLogger("athentose")
        logger.entry()
        callback_url = f'{UcasalConfig.designaciones_bfaresponse_endpoint()}{uuid}/bfaresponse'
        logger.debug(f'Setting callback URL: {callback_url}')
        return callback_url
    

    @classmethod
    def change_state_integration(cls, uuid: str, state: int, auth_token: str):
        """
        Notifica al backend UCASAL el cambio de estado de una Designación.
        Usa PATCH con Authorization Bearer, contra el endpoint configurado en
        endpoint.change_designaciones.url
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
        
