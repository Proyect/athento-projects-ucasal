# -*- coding: utf-8 -*-
# Operation properties
from django.http import HttpResponse
from operations.classes.document_operation import DocumentOperation
from django.utils.translation import gettext as _
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from utils import DesignacionesStates
from external_services.ucasal.designaciones_services import DesignacionesServices
from external_services.ucasal.ucasal_services import UcasalServices
from utils import UcasalConfig
from core.exceptions import AthentoseError
from datetime import datetime
import pytz
from series.models import Serie
from file.foperations import op_send_by_email

class RechazaDesignaciones (DocumentOperation):
    version = "1.0"
    name = _("RechazoDesignaciones")
    description = _("Rechaza las Designaciones Docente y la mueve al espacio Papelera")
    configuration_parameters = { }
    _logger:SpLogger = SpLogger("athentose","RechazaDesignaciones")

    def execute(self, *args, **kwargs):
        flogger:SpFeatureLogger = NullSpFeatureLogger()  
        try:
            logger = self._logger            
            logger.entry()

            fil = self.document
            uuid = str(fil.uuid)

            flogger = SpFeatureLogger.getLogger(fil)

            lifecycle_state = fil.life_cycle_state.name

            AREA_BY_STATE = {
                DesignacionesStates.pendiente_validacion_ld:       "Legajo Docente",
                DesignacionesStates.pendiente_validacion_personal: "Personal",
                DesignacionesStates.pendiente_validacion_rrhh:     "RRHH",
                DesignacionesStates.pendiente_firma_otp:           "Vicerrector Administrativo",
            }

            if lifecycle_state in AREA_BY_STATE:
                area = AREA_BY_STATE[lifecycle_state]
                motivo_rechazo = fil.gmv('metadata.designaciones_motivo_de_rechazo')
                if not motivo_rechazo or motivo_rechazo.strip() == "":
                    return logger.exit({"msg" : f"Debe completar el Motivo de Rechazo", "msg_type" : "warning"})

                fil.change_life_cycle_state(DesignacionesStates.rechazado)
                tz = pytz.timezone('America/Argentina/Buenos_Aires')
                date_str = datetime.now(tz=tz).strftime('%Y-%m-%d')   
                fil.set_metadata('metadata.designaciones_fecha_rechazo', date_str, overwrite=True)               
                
                serie_papelera = Serie.objects.filter(uuid='69cf403f-ff0d-4207-9d9a-a1d8a816b6c8').first()
                fil.move_to_serie(serie_papelera)

                auth_token = UcasalServices.get_auth_token(
                    user=UcasalConfig.token_svc_user(),
                    password=UcasalConfig.token_svc_password()
                )    
                #Envia a estado 1 la designación rechazada
                response = DesignacionesServices.change_state_integration(uuid=uuid, state=1, auth_token=auth_token)
                fil.set_feature('Response estado 1', response.text)
                fil.set_feature('Status Code 1', response.status_code)
                fil.change_life_cycle_state(DesignacionesStates.rechazado) 

                op_send_by_email.run(
                    uuid,
                    notifications_template="designaciones_notificacion_rechazo",
                    send_to_groups="Legajo Docente",
                    area=area,
                )          
                return logger.exit({"msg" : f"La Designacion Docente con UUID: {uuid} fue rechazada", "msg_type" : "success", "redirect_url" : "/dashboard/"})
                        
        except FileNotFoundError as e:
            flogger.error(f'Error al procesar el archivo: {str(e)}')
            return logger.exit({"msg": str(e), "msg_type": "error"}, exc_info=True)

        except AthentoseError as e:
            flogger.error(f'Error en la operación: {str(e)}')
            return logger.exit({"msg": str(e), "msg_type": "error"}, exc_info=True)

        except Exception as e:
            flogger.error(f'Error inesperado: {str(e)}')
            return logger.exit({"msg": str(e), "msg_type": "error"}, exc_info=True)
    
VERSION = RechazaDesignaciones.version
NAME = RechazaDesignaciones.name
DESCRIPTION = RechazaDesignaciones.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = RechazaDesignaciones.configuration_parameters

def run(uuid=None, **params):
    return RechazaDesignaciones(uuid, **params).run()