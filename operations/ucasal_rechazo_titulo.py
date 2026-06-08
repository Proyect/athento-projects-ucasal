# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from django.http import HttpResponse
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger
from file.foperations import op_send_by_email
from custom.ucasal2.utils  import TituloStates


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

        try:
            
            # 2. Obtener motivo de rechazo (si viene por parámetros) o usar '-'
            motivo = kwargs.get("reason") or kwargs.get("motivo") or "-"
            motivo = str(motivo)

            # 3. Actualizar metadatos de rechazo / firma
            fil.set_metadata(
                "metadata.form_titulo_rechazar",
                motivo,
                overwrite=True,
            )
            fil.set_metadata(
                "metadata.form_titulo_firmar",
                "",
                overwrite=True,
            )

            # 4. Cambiar estado lógico (metadato) y ciclo de vida al estado final RECHAZADO
            # Debe coincidir exactamente con el nombre configurado en el ciclo de vida
            fil.set_metadata("estado", "RECHAZADO", overwrite=True)
            fil.change_life_cycle_state("RECHAZADO")

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
            return logger.exit(HttpResponse("Título rechazado exitosamente"))

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