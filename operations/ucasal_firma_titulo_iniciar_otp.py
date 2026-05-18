# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from django.http import HttpResponse
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from file.models import File, DocumentRelation

class IniciaFirmaTituloOTP(DocumentOperation):
    version = "1.0"
    name = _("IniciaFirmaTituloOTP")
    description = _(
        "Pasa el título al estado pendiente_firma_otp para iniciar firma digital"
    )
    configuration_parameters = {}
    _logger: SpLogger = SpLogger.getLogger("athentose")

    def execute(self, *args, **kwargs):
        flogger: SpFeatureLogger = NullSpFeatureLogger()
        logger = self._logger
        logger.entry()

        fil = self.document
        uuid = str(fil.uuid)

        try:
            relaciones = DocumentRelation.objects.filter(parent=fil) 
            for rel in relaciones:
                hijo = rel.child
                tipo_relacion = rel.relation_type
                print(f"Hijo: {hijo.uuid}, Tipo: {tipo_relacion}")
        except Exception as e:
            logger.error(f"Error al obtener relaciones: {e}")
            return logger.exit(
                {
                    "msg": f"Error al obtener relaciones para el título {uuid}",
                    "msg_type": "error",
                }
            )

        try:
            flogger = SpFeatureLogger.getLogger(fil)
            flogger.entry("Iniciando proceso de firma OTP para el título...")

            # Leer estado actual
            lifecycle_state = fil.life_cycle_state.name
            estado_meta = fil.gfv("estado") or lifecycle_state

            # Verificar que el estado permita iniciar OTP.
            # Según el ciclo de vida, debe estar en "Pendiente de validacion FSG (secretaria general)".
            if estado_meta != "Pendiente de validacion FSG (secretaria general)":
                raise AthentoseError(
                    _(
                        f"El título está en estado '{estado_meta}' y no puede iniciar el proceso de firma OTP."
                    )
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
            nuevo_estado = "Pendiente de Firma OTP"
            fil.set_metadata("estado", nuevo_estado, overwrite=True)
            fil.change_life_cycle_state(nuevo_estado)

            flogger.debug("Título pasado a estado 'Pendiente de Firma OTP'")
            return logger.exit(
                HttpResponse(
                    _(
                        "Título preparado para firma OTP (estado 'Pendiente de Firma OTP')"
                    ),
                    status=200,
                )
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
