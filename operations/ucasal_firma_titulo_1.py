# -*- coding: utf-8 -*-
# Operation properties
from django.http import HttpResponse
from operations.classes.document_operation import DocumentOperation
from django.utils.translation import gettext as _
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from core.exceptions import AthentoseError

from file.models import File, DocumentRelation


class FirmaTitulo(DocumentOperation):
    """Operación que avanza el estado de un título en el workflow UCASAL.

    Flujo esperado (padre):
      DA -> FD -> FR -> TIT -> FSG
    """

    version = "1.0"
    name = _("FirmaTitulo")
    description = _("Firma un título y lo avanza de estado")
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose", "FirmaTitulo")

    def execute(self, *args, **kwargs):
        flogger: SpFeatureLogger = NullSpFeatureLogger()
        logger = self._logger
        logger.entry()

        # Import diferido para evitar fallos de instalación si ucasal.utils
        # aún no está disponible en el entorno donde se importa la operación.
        from ucasal.utils import TituloStates

        fil = self.document
        uuid = str(fil.uuid)

        # Relación padre-hijo (por ahora solo la listamos; se puede
        # extender para propagar cambios de estado a los hijos).
        try:
            relaciones = DocumentRelation.objects.filter(parent=fil)
            for rel in relaciones:
                hijo = rel.child
                tipo_relacion = rel.relation_type
                print(f"Hijo: {hijo.uuid}, Tipo: {tipo_relacion}")
        except Exception as e:
            logger.error(f"Error al obtener relaciones: {e}")

        try:
            flogger = SpFeatureLogger.getLogger(fil)

            lifecycle_state = fil.life_cycle_state.name if fil.life_cycle_state else ""
            estado_meta = fil.gfv("estado") or lifecycle_state

            # Avanzar en la cadena DA -> FD -> FR -> TIT -> FSG
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

            # Si el estado actual no está en ninguno de los anteriores,
            # consideramos que no puede avanzar con esta operación.
            raise AthentoseError(
                _(
                    "El estado actual del título (%(estado)s) no permite la aprobación."
                )
                % {"estado": estado_meta}
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

VERSION = FirmaTitulo.version
NAME = FirmaTitulo.name
DESCRIPTION = FirmaTitulo.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = FirmaTitulo.configuration_parameters


def run(uuid=None, **params):
    return FirmaTitulo(uuid, **params).run()
