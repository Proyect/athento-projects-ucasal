# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from django.http import HttpResponse
from ucasal.external_services.ucasal.ucasal_services import UcasalServices
from ucasal.utils import UcasalConfig
from ucasal.utils import ActaStates 
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger
uuid_previo_metadata_name =  'metadata.acta_id_acta_previa'
class RechazaActaDeExamen(DocumentOperation):
    version = "1.0"
    name = _("Rechaza Acta de Examen")
    description = _("Rechaza actas de examen que quedaron pedientes")
    configuration_parameters = { }
    _logger:SpLogger = SpLogger("athentose","RechazaActaDeExamen")

    def execute(self, *args, **kwargs):
        try:
            logger = self._logger 

            logger.entry()
            fil = self.document
            uuid = 'N/A'

            fil = self.document
            uuid = str(fil.uuid)

            # Verificar si el documento ya fue firmado con OTP
            firmada_con_opt = fil.gfv('firmada.con.OTP')
            if firmada_con_opt == "1":
                raise AthentoseError(f"El acta ya fue firmada y no puede ser rechazada.")
            motivo = '-'
            # Notificar a UCASAL para que puedan editar el acta
            auth_token = UcasalServices.get_auth_token(user=UcasalConfig.token_svc_user(), password = UcasalConfig.token_svc_password())
            uuid_acta_previa = str(fil.gmv(uuid_previo_metadata_name)).replace('None', '')
            UcasalServices.notify_rejection(auth_token=auth_token, uuid=fil.uuid, previous_uuid = uuid_acta_previa, reason=motivo)
            
            # Cambiar estado a Rechazada (aunque la borremos luego, si hay error invocando a UCASAL, al menos que rechazada en Athento)
            #TODO: forzar transición?
            fil.change_life_cycle_state(ActaStates.rechazada) #, force_transition=True)
            logger.exit(HttpResponse('Acta rechazada exitosamente'))
            # Borrar el acta
            fil.removed = True
            fil.save()

            # Mover el acta al espacio Papelera (Comentado por ahora)
            #fil.move_to_serie(name='papelera')
            return logger.exit(HttpResponse('Acta rechazada exitosamente'))            
      
        except AthentoseError as e:
            return logger.exit(HttpResponse(
            str(e), 
            status='400'
        ), exc_info=True)
        except Exception as e:
            raise logger.exit(e, exc_info=True)
VERSION = RechazaActaDeExamen.version
NAME = RechazaActaDeExamen.name
DESCRIPTION = RechazaActaDeExamen.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = RechazaActaDeExamen.configuration_parameters


def run(uuid=None, **params):
    return RechazaActaDeExamen(uuid, **params).run()        