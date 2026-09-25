# -*- coding: utf-8 -*-
# Operation properties
from contextlib import nullcontext
from operations.classes.document_operation import DocumentOperation
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from django.http import HttpResponse
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger
from file.foperations import op_send_by_email
from custom.ucasal2.utils  import TituloStates
from datetime import datetime
import pytz
import requests
from custom.ucasal2.services import UcasalServices
from custom.ucasal2.config import UcasalConfig
from custom.sp_libs.python.utils import is_digit
from custom.sp_libs.python.auth import get_current_user

class RechazaTitulo(DocumentOperation):
    version = "1.0"
    name = _("Rechaza Título")
    description = _("Rechaza un título si aún no está firmado")
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose", "RechazaTitulo")

    def execute(self, *args, **kwargs):
        logger = self._logger
        logger.entry()

        fil = self.document
        uuid = str(fil.uuid)
        flogger: SpFeatureLogger = SpFeatureLogger.getLogger(fil)
        flogger.entry("Rechazando el título...")

        lifecycle_state = fil.life_cycle_state.name
        estado_meta = lifecycle_state

        AREA_BY_STATE = {
            TituloStates.pendiente_validacion_da:  "DEPARTAMENTO DE ALUMNOS",
            TituloStates.pendiente_validacion_fd:  "DECANO",
            TituloStates.pendiente_validacion_fr:  "RECTOR",
            TituloStates.pendiente_validacion_tit: "TITULOS",
            TituloStates.pendiente_validacion_fsg: "SECRETARIA GRAL",
        }#pendiente a completar con los estados faltantes
        #flogger.entry(f"Datos del documento: {fil}")
        try:
            
            # 2. Obtener motivo de rechazo
            motivo = fil.gmv("metadata.form_titulo_motivo_de_rechazo") or ""
            motivo = str(motivo).strip()

            if (motivo == ""):                
                raise AthentoseError("Debe ingresar un motivo de rechazo para continuar.")            
        
            # 2.b Leer y validar OTP
            otp_str = str(fil.gmv("metadata.titulo_otp") or "").strip()
            if otp_str == "":
                raise AthentoseError("El OTP no puede ser nulo, ingrese un valor válido")
            if not is_digit(otp_str):
                raise AthentoseError(
                    _("'OTP' debe ser un número entero positivo en lugar de '%(otp)s'")
                    % {"otp": otp_str}
                )
            otp = int(otp_str)

            usuario = get_current_user()
            if not usuario or not getattr(usuario, "is_authenticated", False):
                raise AthentoseError("No hay un usuario autenticado para rechazar el título")
            mail_sg = usuario.email or ""
            if not mail_sg:
                raise AthentoseError("No se pudo obtener el mail del usuario autenticado")

            UcasalServices.validate_otp(user=mail_sg, otp=otp)
            fil.set_metadata("metadata.titulo_otp", "", overwrite=True)

            # 3. Actualizar metadatos de rechazo / firma
            fil.set_metadata(
                "metadata.form_titulo_rechazar",
                motivo,
                overwrite=True,
            )


            # 4. Cambiar estado lógico (metadato) y ciclo de vida al estado final RECHAZADO
            # Debe coincidir exactamente con el nombre configurado en el ciclo de vida
            fil.set_metadata("estado", "RECHAZADO", overwrite=True)
            fil.change_life_cycle_state("RECHAZADO")

            try:
                response = requests.post(
                    #"https://backprod.ucasal.edu.ar/testing/titulos/athento/reject",
                    UcasalConfig.titulo_rejection_url(),
                    json={"uuidExpediente": uuid},
                    verify=False,
                )
                flogger.entry(f"Notificación rechazo enviada a UCASAL - Status: {response.status_code}, Response: {response.text[:200]}")
            except Exception as notif_err:
                flogger.entry(f"Error al notificar rechazo a UCASAL: {str(notif_err)}")

            # Guardar fecha de rechazo del título
            tz = pytz.timezone("America/Argentina/Buenos_Aires")
            date_str = datetime.now(tz=tz).strftime("%Y-%m-%d")  # o "%d/%m/%Y" si prefieres 
            fil.set_metadata("metadata.form_titulo_fecha_rechazo", date_str, overwrite=True)

            flogger.debug("Título rechazado exitosamente")

            if estado_meta not in AREA_BY_STATE:
                return logger.exit(
                {
                    "msg_type": "warning",
                    "msg": f"El estado actual del título ({estado_meta}) no permite el rechazo.",
                }
            )

            area = AREA_BY_STATE[estado_meta]
            op_send_by_email.run(
                    uuid,
                    notifications_template="titulos_notificacion_rechazo",
                    send_to_groups="TITULOS",
                    area=area,
                )    
            return logger.exit({
                            "msg_type": "success",
                            "msg": "Título rechazado exitosamente",
                     })

        except AthentoseError as e:
            flogger.error(f"Error rechazando el título: {e}")
            return logger.exit(
                {
                    "msg_type": "error",
                    "msg": f"Error rechazando el título: {e}",
                },
                exc_info=True,
            )

        except Exception as e:  # noqa: BLE001
            flogger.error(f"Error inesperado rechazando el título: {e}")
            return logger.exit(
                {
                    "msg_type": "error",
                    "msg": _("Error inesperado rechazando el título."),
                },
                exc_info=True,
            )


VERSION = RechazaTitulo.version
NAME = RechazaTitulo.name
DESCRIPTION = RechazaTitulo.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = RechazaTitulo.configuration_parameters


def run(uuid=None, **params):
    return RechazaTitulo(uuid, **params).run()