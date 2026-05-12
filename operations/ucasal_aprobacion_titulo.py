# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from django.http import HttpResponse
from django.utils.translation import gettext as _
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from core.exceptions import AthentoseError


class ApruebaTitulo(DocumentOperation):
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

        try:
            flogger = SpFeatureLogger.getLogger(fil)

            # Leer estado actual (lifecycle + metadato 'estado' si lo usas)
            lifecycle_state = fil.life_cycle_state.name
            estado_meta = fil.gfv("estado") or lifecycle_state

            # Flujo real de validaciones de títulos:
            # Pendiente de validacion DA -> FD -> FR -> TIT -> FSG

            if estado_meta == "Pendiente de validacion DA (direccion de alumnos)":
                nuevo_estado = "Pendiente de validacion FD (firma del decano)"
                fil.set_metadata("estado", nuevo_estado, overwrite=True)
                fil.change_life_cycle_state(nuevo_estado)

                return logger.exit(
                    {
                        "msg": f"El título {uuid} avanzó a '{nuevo_estado}'",
                        "msg_type": "success",
                    }
                )

            if estado_meta == "Pendiente de validacion FD (firma del decano)":
                nuevo_estado = "Pendiente de validacion FR (firma del rector)"
                fil.set_metadata("estado", nuevo_estado, overwrite=True)
                fil.change_life_cycle_state(nuevo_estado)

                return logger.exit(
                    {
                        "msg": f"El título {uuid} avanzó a '{nuevo_estado}'",
                        "msg_type": "success",
                    }
                )

            if estado_meta == "Pendiente de validacion FR (firma del rector)":
                nuevo_estado = "Pendiente de Validacion TIT (titulo)"
                fil.set_metadata("estado", nuevo_estado, overwrite=True)
                fil.change_life_cycle_state(nuevo_estado)

                return logger.exit(
                    {
                        "msg": f"El título {uuid} avanzó a '{nuevo_estado}'",
                        "msg_type": "success",
                    }
                )

            if estado_meta == "Pendiente de Validacion TIT (titulo)":
                nuevo_estado = "Pendiente de validacion FSG (secretaria general)"
                fil.set_metadata("estado", nuevo_estado, overwrite=True)
                fil.change_life_cycle_state(nuevo_estado)

                return logger.exit(
                    {
                        "msg": f"El título {uuid} avanzó a '{nuevo_estado}'",
                        "msg_type": "success",
                    }
                )

            # Si no se reconoce el estado, devolver error controlado
            raise AthentoseError(
                _(
                    f"El estado actual del título ({estado_meta}) no permite la aprobación."
                )
            )

        except FileNotFoundError as e:  # noqa: F821,BLE001
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
        except Exception as e:  # noqa: BLE001
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
