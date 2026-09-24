# -*- coding: utf-8 -*-
import requests
from core.exceptions import AthentoseError
from custom.sp_libs.python.logging import SpLogger
from ucasal2.utils import UcasalConfig


class ProgramasServices:
    logger = SpLogger("athentose", "ProgramasServices")

    # TODO: cambiar a True cuando el entorno tenga certificado válido
    VERIFY_CERTIFICATE = False

    @classmethod
    def get_callback_url(cls, uuid: str) -> str:
        base = UcasalConfig.programas_bfaresponse_endpoint().rstrip("/")
        return f"{base}/{uuid}/bfaresponse"

    @classmethod
    def notify_change_state(cls, auth_token: str, uuid: str, state: int):
        logger = cls.logger
        logger.entry()

        try:
            base = UcasalConfig.programas_change_state_svc_url().rstrip("/")
            endpoint = f"{base}/{uuid}"
            data = {"estado": state}
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            logger.debug("[Programas] PATCH %s con payload=%s", endpoint, data)
            resp = requests.patch(
                url=endpoint,
                json=data,
                headers=headers,
                timeout=30,
                verify=cls.VERIFY_CERTIFICATE,
            )

            body = resp.text[:500] if resp.text else "N/A"
            logger.debug("[Programas] Respuesta UCASAL (%s): %s", resp.status_code, body)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.error(
                "[Programas] Error notificando estado %s para %s: %s",
                state,
                uuid,
                str(e),
            )
            raise AthentoseError(
                f"Error notificando estado del programa a UCASAL: {e}"
            ) from e
