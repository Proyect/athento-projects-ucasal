# -*- coding: utf-8 -*-
# Operation properties
from django.http import HttpResponse
from operations.classes.document_operation import DocumentOperation
from django.utils.translation import gettext as _
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from core.exceptions import AthentoseError

from file.models import File, DocumentRelation


class FirmaTitulo(DocumentOperation):
    version = "1.0"
    name = _("FirmaTitulo")
    description = _("Firma un título y lo avanza de estado")
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose","FirmaTitulo")

    def execute(self, *args, **kwargs):
        flogger: SpFeatureLogger = NullSpFeatureLogger()
        logger = self._logger
        logger.entry()

        # Import diferido para evitar fallos de instalación si ucasal.utils
        # aún no está disponible en el entorno donde se importa la operación.
        from ucasal.utils import TituloStates, can_transition

        fil = self.document
        uuid = str(fil.uuid)
        try:
            # Se podrían usar las relaciones padre-hijo en el futuro si se desea
            # propagar el cambio de estado a documentos relacionados.
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

            if not can_transition(estado_meta, TituloStates.firmado):
                raise AthentoseError(
                    _(
                        "Transición no permitida: '%(estado_actual)s' → '%(estado_nuevo)s'"
                    )
                    % {"estado_actual": estado_meta or "", "estado_nuevo": TituloStates.firmado}
                )

            # Cambiar ciclo de vida al estado 'Firmado'
            fil.change_life_cycle_state(TituloStates.firmado)
            # Sincronizar metadata utilizada por integraciones externas
            fil.set_metadata("metadata.lifecycle_state", TituloStates.firmado)
            fil.save()

            return logger.exit(
                {
                    "msg": f"El título {uuid} avanzó a '{TituloStates.firmado}'",
                    "msg_type": "success",
                }
            )

        except FileNotFoundError as e:
            flogger.error(f"Error al procesar el archivo: {e}")
            return logger.exit(
                HttpResponse(str(e), status=404),
                exc_info=True,
            )
        except AthentoseError as e:
            flogger.error(f"Error en la operación de firma de título: {e}")
            return logger.exit(
                HttpResponse(str(e), status=400),
                exc_info=True,
            )
        except Exception as e:
            flogger.error(f"Error inesperado al firmar el título: {e}")
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
