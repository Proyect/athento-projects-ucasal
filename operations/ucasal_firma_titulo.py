# -*- coding: utf-8 -*-
# Operation properties
from django.http import HttpResponse
from operations.classes.document_operation import DocumentOperation
from django.utils.translation import gettext as _
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from core.exceptions import AthentoseError
from ucasal.utils import TituloStates

from file.models import File, DocumentRelation


class FirmaTitulo(DocumentOperation):
    version = "1.0"
    name = _("AprobacionTitulo")
    description = _("Aprueba un título y lo avanza de estado")
    configuration_parameters = {}
    _logger: SpLogger = SpLogger.getLogger("athentose")

    def execute(self, *args, **kwargs):
        flogger: SpFeatureLogger = NullSpFeatureLogger()
        logger = self._logger
        logger.entry()

        fil = self.document
        uuid = str(fil.uuid)

        relaciones = DocumentRelation.objects.filter(parent=fil) 
        try:
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

            lifecycle_state = fil.life_cycle_state.name
            estado_meta = fil.gfv("estado") or lifecycle_state

            if estado_meta == TituloStates.pendiente_validacion_da:
                nuevo_estado = TituloStates.pendiente_validacion_fd
                fil.set_metadata("estado", nuevo_estado, overwrite=True)
                fil.change_life_cycle_state(nuevo_estado)
                return logger.exit(
                    {
                        "msg": f"El título {uuid} avanzó a '{nuevo_estado}'",
                        "msg_type": "success",
                    }
                )

            if estado_meta == TituloStates.pendiente_validacion_fd:
                nuevo_estado = TituloStates.pendiente_validacion_fr
                fil.set_metadata("estado", nuevo_estado, overwrite=True)
                fil.change_life_cycle_state(nuevo_estado)
                return logger.exit(
                    {
                        "msg": f"El título {uuid} avanzó a '{nuevo_estado}'",
                        "msg_type": "success",
                    }
                )

            if estado_meta == TituloStates.pendiente_validacion_fr:
                nuevo_estado = TituloStates.pendiente_validacion_tit
                fil.set_metadata("estado", nuevo_estado, overwrite=True)
                fil.change_life_cycle_state(nuevo_estado)
                return logger.exit(
                    {
                        "msg": f"El título {uuid} avanzó a '{nuevo_estado}'",
                        "msg_type": "success",
                    }
                )

            if estado_meta == TituloStates.pendiente_validacion_tit:
                nuevo_estado = TituloStates.pendiente_validacion_fsg
                fil.set_metadata("estado", nuevo_estado, overwrite=True)
                fil.change_life_cycle_state(nuevo_estado)
                return logger.exit(
                    {
                        "msg": f"El título {uuid} avanzó a '{nuevo_estado}'",
                        "msg_type": "success",
                    }
                )

            raise AthentoseError(
                _(
                    f"El estado actual del título ({estado_meta}) no permite la aprobación."
                )
            )

        except FileNotFoundError as e:
            flogger.error(f"Error al procesar el archivo: {e}")
            return logger.exit(
                HttpResponse(str(e), status=404),
                exc_info=True,
            )
        except AthentoseError as e:
            flogger.error(f"Error en la operación de aprobación de título: {e}")
            return logger.exit(
                HttpResponse(str(e), status=400),
                exc_info=True,
            )
        except Exception as e:
            flogger.error(f"Error inesperado al aprobar el título: {e}")
            return logger.exit(
                HttpResponse(str(e), status=500),
                exc_info=True,
            )


VERSION = ApruebaTitulo.version
NAME = ApruebaTitulo.name
DESCRIPTION = ApruebaTitulo.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = ApruebaTitulo.configuration_parameters


def run(uuid=None, **params):
    return ApruebaTitulo(uuid, **params).run()
