# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from django.http import HttpResponse
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger


class RechazaTitulo(DocumentOperation):
    version = "1.0"
    name = _("Rechaza Título")
    description = _("Rechaza un título si aún no está firmado")
    configuration_parameters = {}
    _logger: SpLogger = SpLogger.getLogger("athentose")

    def execute(self, *args, **kwargs):
        logger = self._logger
        logger.entry()

        fil = self.document
        uuid = str(fil.uuid)
        flogger: SpFeatureLogger = SpFeatureLogger.getLogger(fil)
        flogger.entry("Rechazando el título...")

        try:
            # 1. Verificar que el título no esté ya marcado como firmado
            firmada = fil.gfv("metadata.form_titulo_firmar")
            if firmada == "ok":
                raise AthentoseError(
                    _("El título ya fue firmado y no puede ser rechazado.")
                )

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
