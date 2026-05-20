# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from core.exceptions import AthentoseError
from file.foperations import op_send_by_email
from file.models import File
from django.utils.translation import gettext as _
from django.http import HttpResponse
from external_services.ucasal.ucasal_services import UcasalServices
from utils import UcasalConfig
from utils import ActaStates 
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger 
from model.ucasal.exceptions import UcasalServiceError

uuid_previo_metadata_name =  'metadata.acta_id_acta_previa'
class RechazaActaDeExamen(DocumentOperation):
    version = "1.0"
    name = _("Rechaza Acta de Examen")
    description = _("Rechaza actas de examen que quedaron pendientes")
    configuration_parameters = { }
    _logger:SpLogger = SpLogger.getLogger("athentose")

    def execute(self, *args, **kwargs):
        logger = self._logger
        fil = self.document
        uuid = str(getattr(fil, "uuid", "N/A"))
        flogger = SpFeatureLogger.getLogger(fil) if fil is not None else logger
        try:
            logger.entry()
            fil:File = self.document
            flogger.entry('Rechazando el acta...')

            # Verificar si el documento ya fue firmado con OTP
            firmada_con_opt = fil.gfv('firmada.con.OTP')
            if firmada_con_opt == "1":
                raise AthentoseError(f"El acta ya fue firmada y no puede ser rechazada.")
            motivo = '-'
            # Cambiar estado a Rechazada (aunque la borremos luego, si hay error invocando a UCASAL, al menos que rechazada en Athento)
            fil.change_life_cycle_state(ActaStates.rechazada) 

            # Notificar a UCASAL para que puedan editar el acta
            auth_token = UcasalServices.get_auth_token(user=UcasalConfig.token_svc_user(), password = UcasalConfig.token_svc_password())
            uuid_acta_previa = str(fil.gmv(uuid_previo_metadata_name)).replace('None', '')
            UcasalServices.notify_rejection(auth_token=auth_token, uuid=fil.uuid, previous_uuid = uuid_acta_previa, reason=motivo)
            flogger.debug('Acta rechazada exitosamente')
            # Borrar el acta
            fil.removed = True
            fil.save()

            # Mover el acta al espacio Papelera (Comentado por ahora)
            #fil.move_to_serie(name='papelera')
            return logger.exit(HttpResponse('Acta rechazada exitosamente'))            
      
        except AthentoseError as e:
            flogger.error(f'Error rechazando el acta: {e}')
            return logger.exit({
                  'msg_type': 'error',
                  'msg': f'Error rechazando el acta: {e}'
                }, exc_info=True)
        except UcasalServiceError as e:
            flogger.error(f'Error notificando el rechazo del acta: {e}')           
            fil.set_metadata('metadata.acta_error_servicio_externo', True, overwrite=True)
            mail_params = {
                'send_to_groups': 'SISTEMAS', 
                'notifications_template': 'ucasal2_error_in_ucasal_service_call_notification', 
                'error': e.detailed_message(),
                'url': fil.get_url_file_view(),
                #'send_to': '', 
                #'send_to_metadata_user': '',
            }
            op_send_by_email.run(uuid, **mail_params)
            return logger.exit({
                  'msg_type': 'error',
                  'msg': str(e)
                }, 
                exc_info=True,
                additional_info=e.to_dict()
            )
        except Exception as e:
            flogger.error(f'Error inesperado notificando el rechazo del acta: {e}')                      
            return logger.exit({
                  'msg_type': 'error',
                  'msg': 'Error inesperado al rechazar el acta.'
                }, exc_info=True)
        
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