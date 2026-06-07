# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from django.http import HttpResponse
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from file.models import File  # , DocumentRelation
from custom.ucasal2.utils import TituloStates

class IniciaFirmaTituloOTP(DocumentOperation):
    version = "1.0"
    name = _("IniciaFirmaTituloOTP")
    description = _(
        "Pasa el título al estado pendiente_firma_otp para iniciar firma digital"
    )
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose", "IniciaFirmaTituloOTP")

    def execute(self, *args, **kwargs):
        flogger: SpFeatureLogger = NullSpFeatureLogger()
        logger = self._logger
        logger.entry()

        fil = self.document
        uuid = str(fil.uuid)

        # try:
        #     relaciones = DocumentRelation.objects.filter(parent=fil) 
        #     for rel in relaciones:
        #         hijo = rel.child
        #         tipo_relacion = rel.relation_type
        #         print(f"Hijo: {hijo.uuid}, Tipo: {tipo_relacion}")
        # except Exception as e:
        #     logger.error(f"Error al obtener relaciones: {e}")
        #     return logger.exit(
        #         {
        #             "msg": f"Error al obtener relaciones para el título {uuid}",
        #             "msg_type": "error",
        #         }
        #     )

        try:
            flogger = SpFeatureLogger.getLogger(fil)
            flogger.entry("Iniciando proceso de firma OTP para el título...")

            # Leer estado actual
            lifecycle_state = fil.life_cycle_state.name if fil.life_cycle_state else ""
            estado_meta = fil.gfv("estado") or lifecycle_state

            # Verificar que el estado permita iniciar OTP.
            # Según el ciclo de vida, debe estar en pendiente_validacion_fsg.
            if estado_meta != TituloStates.pendiente_validacion_fsg:
                raise AthentoseError(
                    _(
                        "El título está en estado '%(estado)s' y no puede iniciar el "
                        "proceso de firma OTP."
                    )
                    % {"estado": estado_meta}
                )

            # Limpiar cualquier rechazo previo
            fil.set_metadata("metadata.form_titulo_rechazar", "", overwrite=True)

            # Opcional: marcar que está en proceso de firma
            fil.set_metadata(
                "metadata.form_titulo_firmar",
                "pendiente_otp",
                overwrite=True,
            )

            # Cambiar estado lógico y de lifecycle a 'Pendiente de Firma OTP'
            nuevo_estado = TituloStates.pendiente_firma_otp
            fil.set_metadata("estado", nuevo_estado, overwrite=True)
            fil.change_life_cycle_state(nuevo_estado)

            flogger.debug("Título pasado a estado 'Pendiente de Firma OTP'")
            return logger.exit(
                {
                    "msg": _(
                        "Título preparado para firma OTP (estado 'Pendiente de Firma OTP')"
                    ),
                    "msg_type": "success",
                }
            )

        except AthentoseError as e:
            flogger.error(f"Error iniciando firma OTP del título: {e}")
            return logger.exit(
                HttpResponse(str(e), status=400),
                exc_info=True,
            )
        except Exception as e:  # noqa: BLE001
            flogger.error(f"Error inesperado iniciando firma OTP del título: {e}")
            return logger.exit(
                HttpResponse(
                    _(
                        "Error inesperado al iniciar el proceso de firma OTP del título."
                    ),
                    status=500,
                ),
                exc_info=True,
            )


VERSION = IniciaFirmaTituloOTP.version
NAME = IniciaFirmaTituloOTP.name
DESCRIPTION = IniciaFirmaTituloOTP.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = IniciaFirmaTituloOTP.configuration_parameters


def run(uuid=None, **params):
    return IniciaFirmaTituloOTP(uuid, **params).run()
