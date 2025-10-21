# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from operations.enums import ProcessOperationParameterType, ProcessOperationParameterChoiceType
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from file.models import File
from series.models import Serie
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger

from ucasal.utils import sector_metadata_name, nro_revision_metadata_name, uuid_previo_metadata_name, serie_actas_revisadas_name, acta_examen_doctype_name

class GdeAsignarEspacioActaExamen(DocumentOperation):
    version = "1.0"
    name = _("Asignar espacio a nueva acta de exámen")
    description = _("Asigna el acta recién creada al espacio que coresponda según el nro de sector")
    configuration_parameters = { }
    _logger:SpLogger = SpLogger("athentose", "GdeAsignarEspacioActaExamen")

    def execute(self, *args, **kwargs):
        try:
            logger = self._logger 

            print('ucasal_asignar_espacio_acta_examen.execute() - ENTER')
            logger.entry()
            uuid = 'N/A'

            fil = self.document
            uuid = str(fil.uuid)
            

            print(f"Procesando nueva acta de exámen '{uuid}'...")
            logger.debug(f"Procesando nueva acta de exámen '{uuid}'...")

            ## Mover el acta al espacio correspondiente al sector
            # Leer el sector


            sector = str(fil.gmv(sector_metadata_name))
            
            if not sector.isdigit():
                raise AthentoseError(f"El valor '{sector}' no es válido para el campo 'Nro sector' ({sector_metadata_name}) en el acta '{uuid}'.")

            sector = int(sector)
            # Obtener espacio destino a partir del nro de sector
            serie_destino = self._get_target_serie(fil=fil, sector=sector) 

            ## Si el acta una revisión de otra existente, mover la original al espacio "Actas Revisadas"
            # Validación conjunta de 'Nro de Revisión' y 'UUID previo'. Deben ser ambos vacíos o ambos con valor
            # Validar Nro de Revisión
            nro_revision = str(fil.gmv(nro_revision_metadata_name)).replace('None', '')
            if len(nro_revision) == 0:
                raise AthentoseError(f"El acta '{uuid}' no indica Nro de Revisión")

            if len(nro_revision) > 0 and not nro_revision.isdigit():
                raise AthentoseError(f"El acta '{uuid}' indica un Nro de Revisión que no es numérico: {nro_revision})")

            # Validar que el acta revisada existe (si se indicó un nro de revisión)
            acta_previa = None
            nro_revision = int(nro_revision)
            if nro_revision > 0:
                uuid_previo = str(fil.gmv(uuid_previo_metadata_name)).replace('None', '')
                if len(uuid_previo) > 0:
                    acta_previa = self._get_acta(uuid_previo)
                    if not acta_previa or acta_previa.doctype.name != acta_examen_doctype_name:
                      raise AthentoseError(f"El acta '{uuid}' indica un UUID previo inválido '{uuid_previo}': No existe un acta con ese UUID.")
                else:
                      raise AthentoseError(f"El acta '{uuid}' indica un nro de revisión '{nro_revision}' pero el UUID previo es inválido: '{uuid_previo}'.")
            
            # Mover el acta original al espacio Actas Revisadas (podría venir un acta que con revisión > 0
            # que fue rechazada por el docente. Entonces el uuid de acta previa seguramente ya fue movido
            # al espacio ACTAS REVISADAS. No habría problema en principio...) 
            if acta_previa:
                print("Moviendo acta revisada al espacio 'Actas Revisadas'")
                logger.debug("Moviendo acta revisada al espacio 'Actas Revisadas'")
                serie_actas_revisadas = Serie.objects.get(name=serie_actas_revisadas_name)  
                acta_previa.move_to_serie(serie_actas_revisadas)
            
            # Mover el acta nueva a su serie según el sector indicado
            fil.move_to_serie(serie_destino)

            print(f"Nueva acta de exámen '{uuid}' procesada exitosamente (movida al espacio '{serie_destino}')")
            logger.debug(f"Nueva acta de exámen '{uuid}' procesada exitosamente (movida al espacio '{serie_destino}')")

            print('ucasal_asignar_espacio_acta_examen.execute() - EXIT')

            return {
              'msg_type': 'success',
              'msg': 'Nueva acta procesada con éxito',
            }
        except AthentoseError as error:
            logger.error(f"Error asignando espacio al acta '{uuid}': {str(error)}", exc_info=True)
            print(f"Error asignando espacio al acta '{uuid}': {str(error)}")
            fil.set_feature('error.proceso.nueva.acta', str(error))
            return logger.exit(
                {
                  'msg_type': 'error',
                  'msg': f'Error asignando el espacio al acta. {error}'
                },
                
                'Error asignando el espacio al acta.',
                additional_info= {"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
                exc_info=True  
            )        
        except Exception as error:
            print(f"Error inesperado asignando espacio al acta '{uuid}: {error}")
            print('ucasal_asignar_espacio_acta_examen.execute() - EXIT - With error')
            fil.set_feature('error.proceso.nueva.acta', str(error))
            return logger.exit(
                {
                  'msg_type': 'error',
                  'msg': 'Error inesperado asignando el espacio al acta. Por favor revise los logs.'
                },
                'Error inesperado asignando espacio al acta',
                additional_info= {"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
                exc_info=True
            )  

    def _get_target_serie(self, fil: File = None, sector: int = None):
        logger = self._logger
        logger.debug("_get_target_serie - ENTER")
        logger.debug(f"params: File={fil}, sector={sector}")
        # Series en el team actual
        team_series = fil.serie.team.serie_set.all()
        logger.debug(f"team_series = {team_series}")
        
        
        start_string = str(sector).rjust(3, '0') + '_'
        logger.debug(f"start_string = {start_string}")
        
        target_series = [s for s in team_series if s.name.startswith(start_string)]
        logger.debug(f"target_series = {target_series}")

        if len(target_series) != 1:
          raise AthentoseError(f"Se econtraron {len(target_series)} series en lugar de UNA Y SÓLO UNA donde asignar el acta '{fil.uuid}', que corresponda al sector '{sector}' indicado.")

        logger.debug("_get_target_serie - EXIT")
      
        return target_series[0]
    
    def _get_acta(self, uuid: str):
        try:
           return File.objects.get(uuid=uuid) 
        except File.DoesNotExist:
            return None
VERSION = GdeAsignarEspacioActaExamen.version
NAME = GdeAsignarEspacioActaExamen.name
DESCRIPTION = GdeAsignarEspacioActaExamen.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = GdeAsignarEspacioActaExamen.configuration_parameters


def run(uuid=None, **params):
    return GdeAsignarEspacioActaExamen(uuid, **params).run()