# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from django.http import HttpResponse
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger
from file.foperations import op_send_by_email
from django_currentuser.middleware import get_current_user
from custom.ucasal2.external_services.ucasal.ucasal_services import UcasalServices
from custom.ucasal2.utils import ProgramasStates, is_digit
from datetime import datetime
import pytz
import requests

class RechazaPrograma(DocumentOperation):
    version = "1.0"
    name = _("Rechaza Programas")
    description = _("Rechaza un programa si aún no está firmado")
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose", "RechazaProgramas")

    # Estados desde los que se puede rechazar -> area a notificar
    AREA_BY_STATE = {
        ProgramasStates.pendiente_validacion_doc: "Pendiente de Validación Docente",
        ProgramasStates.pendiente_firma_otp: "Pendiente de Firma OTP",
    }

    def execute(self, *args, **kwargs):
        flogger: SpFeatureLogger = NullSpFeatureLogger()
        logger = self._logger
        logger.entry()

        fil = self.document
        uuid = str(fil.uuid)
        flogger: SpFeatureLogger = SpFeatureLogger.getLogger(fil)
        flogger.entry("Rechazando el programa...")
        flogger.entry(f"Datos del documento: UUID {uuid}")

        try:
            # 1. Validar que el estado actual permite el rechazo (antes de mutar)
            lifecycle_state = fil.life_cycle_state.name if fil.life_cycle_state else ""
            estado_meta = fil.gfv("estado") or lifecycle_state

            if estado_meta not in self.AREA_BY_STATE:
                raise AthentoseError(
                    f"El estado actual del programas ({estado_meta or 'sin estado'}) no permite el rechazo."
                )
            area = self.AREA_BY_STATE[estado_meta]

            # 2. Obtener motivo de rechazo
            motivo = str(fil.gmv("metadata.programas_motivo_rechazo") or "").strip()
            if motivo == "":
                raise AthentoseError("Debe ingresar un motivo de rechazo para continuar.")

            otp_str = str(fil.gmv("metadata.programas_otp") or "").strip()
            if otp_str == "":
                flogger.entry("El OTP no puede ser nulo, ingrese un valor válido")
                raise AthentoseError("El OTP no puede ser nulo, ingrese un valor válido")
            if not is_digit(otp_str):
                flogger.entry(f"'OTP' debe ser un número entero positivo en lugar de '{otp_str}'")
                raise AthentoseError(
                    _("'OTP' debe ser un número entero positivo en lugar de '%(otp)s'")
                    % {"otp": otp_str}
                )

            otp = int(otp_str)

            usuario = get_current_user()
            if not usuario or not getattr(usuario, "is_authenticated", False):
                flogger.entry("No hay un usuario autenticado para rechazar el programa")
                raise AthentoseError("No hay un usuario autenticado para rechazar el programa")
            mail_sg = usuario.email or ""

            UcasalServices.validate_otp(user=mail_sg, otp=otp)

            # 3. Persistir motivo y cambiar estado a RECHAZADO
            fil.set_metadata(
                "metadata.programas_motivo_rechazo",
                motivo,
                overwrite=True,
            )
            fil.set_metadata("estado", ProgramasStates.rechazado, overwrite=True)

            if fil.life_cycle_state:
                fil.change_life_cycle_state(ProgramasStates.rechazado)

            # 4. Notificar rechazo a UCASAL
            try:
                response = requests.post(
                    "https://sistemasweb-desa.ucasal.edu.ar/v1/titulos/update-rejected",
                    json={"status": "4", "uuid": uuid},
                    verify=False,
                    timeout=30,
                )
                flogger.entry(f"Notificación rechazo enviada a UCASAL - Status: {response.status_code}, Response: {response.text[:200]}")
            except Exception as notif_err:
                flogger.entry(f"Error al notificar rechazo a UCASAL: {str(notif_err)}")

            # 5. Guardar fecha de rechazo del programa
            tz = pytz.timezone("America/Argentina/Buenos_Aires")
            date_str = datetime.now(tz=tz).strftime("%Y-%m-%d")
            fil.set_metadata("metadata.programas_fecha_rechazo", date_str, overwrite=True)

            flogger.debug("Programa rechazado exitosamente")

            op_send_by_email.run(
                uuid,
                notifications_template="titulos_notificacion_rechazo",
                send_to_groups="TITULOS",
                area=area,
            )
            return logger.exit(HttpResponse("Programa rechazado exitosamente"))

        except AthentoseError as e:
            flogger.error(f"Error rechazando el programa: {e}")
            return logger.exit(
                {
                    "msg_type": "error",
                    "msg": f"Error rechazando el programa: {e}",
                },
                exc_info=True,
            )

        except Exception as e:  # noqa: BLE001
            flogger.error(f"Error inesperado rechazando el programa: {e}")
            return logger.exit(
                {
                    "msg_type": "error",
                    "msg": _("Error inesperado rechazando el programa."),
                },
                exc_info=True,
            )

VERSION = RechazaPrograma.version
NAME = RechazaPrograma.name
DESCRIPTION = RechazaPrograma.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = RechazaPrograma.configuration_parameters


def run(uuid=None, **params):
    return RechazaPrograma(uuid, **params).run()
