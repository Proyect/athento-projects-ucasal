# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from django.utils.translation import gettext as _
from django.http import HttpResponse

from core.exceptions import AthentoseError
from custom.ucasal2.utils import TituloStates


class FirmaTituloOTP(DocumentOperation):
    """Avanza el título por los estados de firma hasta 'Firmado'."""

    version = "1.0"
    name = _("FirmaTituloOTP")
    description = _("Avanza el título hasta el estado Firmado")
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose", "FirmaTituloOTP")

    def execute(self, *args, **kwargs):  # noqa: D401
        flogger: SpFeatureLogger = NullSpFeatureLogger()
        logger = self._logger
        logger.entry()

        fil_padre = self.document
        uuid_padre = str(fil_padre.uuid)

        try:
            flogger = SpFeatureLogger.getLogger(fil_padre)
            flogger.entry(f"UUID padre: {uuid_padre}")

            fil_padre.change_life_cycle_state(TituloStates.pendiente_firma_otp)
            fil_padre.set_metadata(
                "estado",
                TituloStates.pendiente_firma_otp,
                overwrite=True,
            )
            fil_padre.change_life_cycle_state(TituloStates.pendiente_blockchain)
            fil_padre.set_metadata(
                "estado",
                TituloStates.pendiente_blockchain,
                overwrite=True,
            )
            fil_padre.change_life_cycle_state(TituloStates.firmado)
            fil_padre.set_metadata("estado", TituloStates.firmado, overwrite=True)
            flogger.entry("Ambos documentos firmados. Estado cambiado a 'Firmado'")

            return logger.exit(
                {
                    "msg": _("Título firmado."),
                    "msg_type": "success",
                }
            )

        except AthentoseError as e:
            error_msg = f"Error en la operación de firma de título OTP: {str(e)}"
            flogger.error(error_msg)
            logger.error(error_msg)
            return logger.exit(HttpResponse(str(e), status=400), exc_info=True)
        except Exception as e:  # noqa: BLE001
            error_msg = f"Error inesperado en la operación de firma de título OTP: {str(e)}"
            flogger.error(error_msg)
            logger.error(error_msg)
            return logger.exit(HttpResponse(str(e), status=500), exc_info=True)


VERSION = FirmaTituloOTP.version
NAME = FirmaTituloOTP.name
DESCRIPTION = FirmaTituloOTP.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = FirmaTituloOTP.configuration_parameters


def run(uuid=None, **params):
    return FirmaTituloOTP(uuid, **params).run()