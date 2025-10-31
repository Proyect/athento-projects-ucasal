# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from operations.enums import ProcessOperationParameterType, ProcessOperationParameterChoiceType
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from model.File import File, Serie
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger

from ucasal.utils import (
    titulo_doctype_name,
    serie_titulos_name,
    serie_titulos_pendiente_ua_name,
    serie_titulos_pendiente_rector_name,
    serie_titulos_pendiente_sg_name,
    serie_titulos_emitidos_name,
    serie_titulos_rechazados_name,
    TituloStates
)


class GdeAsignarEspacioTitulo(DocumentOperation):
    version = "1.0"
    name = _("Asignar espacio a nuevo título")
    description = _("Asigna el título recién creado al espacio que corresponde según su estado")
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose", "GdeAsignarEspacioTitulo")

    def execute(self, *args, **kwargs):
        try:
            logger = self._logger
            logger.entry()

            print('titulos_asignar_espacio.execute() - ENTER')
            uuid = 'N/A'

            fil = self.document
            uuid = str(fil.uuid)

            print(f"Procesando nuevo título '{uuid}'...")
            logger.debug(f"Procesando nuevo título '{uuid}'...")

            # Verificar doctype
            if fil.doctype.name != titulo_doctype_name:
                logger.debug(
                    f"Documento '{uuid}' no es un título (doctype: {fil.doctype.name}), saltando..."
                )
                return {
                    'msg_type': 'info',
                    'msg': f'Documento no es un título (doctype: {fil.doctype.name})'
                }

            # Obtener estado actual del ciclo de vida
            estado_actual = fil.life_cycle_state.name

            print(f"Estado actual del título: '{estado_actual}'")
            logger.debug(f"Estado actual del título: '{estado_actual}'")

            # Mapeo de estados a series
            estado_serie_map = {
                TituloStates.recibido: serie_titulos_name,
                TituloStates.pendiente_aprobacion_ua: serie_titulos_pendiente_ua_name,
                TituloStates.aprobado_ua: serie_titulos_pendiente_rector_name,
                TituloStates.pendiente_aprobacion_r: serie_titulos_pendiente_rector_name,
                TituloStates.aprobado_r: serie_titulos_pendiente_sg_name,
                TituloStates.pendiente_firma_sg: serie_titulos_pendiente_sg_name,
                TituloStates.firmado_sg: serie_titulos_emitidos_name,
                TituloStates.pendiente_blockchain: serie_titulos_pendiente_sg_name,
                TituloStates.registrado_blockchain: serie_titulos_emitidos_name,
                TituloStates.titulo_emitido: serie_titulos_emitidos_name,
                TituloStates.rechazado: serie_titulos_rechazados_name,
            }

            serie_destino_nombre = estado_serie_map.get(estado_actual, serie_titulos_name)

            print(f"Serie destino para estado '{estado_actual}': '{serie_destino_nombre}'")
            logger.debug(f"Serie destino para estado '{estado_actual}': '{serie_destino_nombre}'")

            # Obtener la serie destino
            try:
                serie_destino = Serie.objects.get(name=serie_destino_nombre)
            except Serie.DoesNotExist:
                logger.warning(
                    f'Serie "{serie_destino_nombre}" no encontrada, usando "{serie_titulos_name}"'
                )
                try:
                    serie_destino = Serie.objects.get(name=serie_titulos_name)
                except Serie.DoesNotExist:
                    raise AthentoseError(
                        f'No se encontró la serie "{serie_titulos_name}" para asignar el título "{uuid}".'
                    )

            # Mover documento a la serie correspondiente
            fil.move_to_serie(serie_destino)

            print(
                f"Nuevo título '{uuid}' procesado exitosamente (movido al espacio '{serie_destino_nombre}')"
            )
            logger.debug(
                f"Nuevo título '{uuid}' procesado exitosamente (movido al espacio '{serie_destino_nombre}')"
            )

            print('titulos_asignar_espacio.execute() - EXIT')

            return {
                'msg_type': 'success',
                'msg': 'Nuevo título procesado con éxito',
            }

        except AthentoseError as error:
            logger.error(
                f"Error asignando espacio al título '{uuid}': {str(error)}",
                exc_info=True
            )
            print(f"Error asignando espacio al título '{uuid}': {str(error)}")
            fil.set_feature('error.proceso.nuevo.titulo', str(error))
            return logger.exit(
                {
                    'msg_type': 'error',
                    'msg': f'Error asignando el espacio al título. {error}'
                },
                'Error asignando el espacio al título.',
                additional_info={
                    "doctype": fil.doctype.label,
                    "doctitle": fil.filename,
                    "uuid": uuid
                },
                exc_info=True
            )

        except Exception as error:
            print(f"Error inesperado asignando espacio al título '{uuid}: {error}")
            print('titulos_asignar_espacio.execute() - EXIT - With error')
            fil.set_feature('error.proceso.nuevo.titulo', str(error))
            return logger.exit(
                {
                    'msg_type': 'error',
                    'msg': 'Error inesperado asignando el espacio al título. Por favor revise los logs.'
                },
                'Error inesperado asignando espacio al título',
                additional_info={
                    "doctype": fil.doctype.label,
                    "doctitle": fil.filename,
                    "uuid": uuid
                },
                exc_info=True
            )


VERSION = GdeAsignarEspacioTitulo.version
NAME = GdeAsignarEspacioTitulo.name
DESCRIPTION = GdeAsignarEspacioTitulo.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = GdeAsignarEspacioTitulo.configuration_parameters


def run(uuid=None, **params):
    return GdeAsignarEspacioTitulo(uuid, **params).run()

