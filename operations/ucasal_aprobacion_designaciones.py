# -*- coding: utf-8 -*-
# Operation properties
from django.http import HttpResponse
from operations.classes.document_operation import DocumentOperation
from django.utils.translation import gettext as _
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from utils import DesignacionesStates
from core.exceptions import AthentoseError
from file.foperations import op_send_by_email

class ApruebaDesignaciones (DocumentOperation):
    version = "1.0"
    name = _("AprobacionDesignaciones")
    description = _("Aprueba las Designaciones Docente y la cambia de Estado")
    configuration_parameters = { }
    _logger:SpLogger = SpLogger("athentose","ApruebaDesignaciones")

    def execute(self, *args, **kwargs):
        flogger:SpFeatureLogger = NullSpFeatureLogger()  
        try:
            logger = self._logger            
            logger.entry()

            fil = self.document
            uuid = str(fil.uuid)

            flogger = SpFeatureLogger.getLogger(fil)

            lifecycle_state = fil.life_cycle_state.name

            if lifecycle_state == DesignacionesStates.pendiente_validacion_ld:
                fil.change_life_cycle_state(DesignacionesStates.pendiente_validacion_personal) 
                op_send_by_email.run(
                    uuid,
                    notifications_template='designaciones_notificacion_validacion',
                    send_to_groups='Personal',
                    area='Legajo Docente'
                )            
                return logger.exit({"msg" : f"Las Designaciones Docente con UUID: {uuid} fue aprobada exitosamente", "msg_type" : "success"})
            
            if lifecycle_state == DesignacionesStates.pendiente_validacion_personal:
                fil.change_life_cycle_state(DesignacionesStates.pendiente_validacion_rrhh) 
                op_send_by_email.run(
                    uuid,
                    notifications_template='designaciones_notificacion_validacion',
                    send_to_groups='RRHH',
                    area='Personal'
                ) 
                return logger.exit({"msg" : f"Las Designaciones Docente con UUID: {uuid} fue aprobada exitosamente", "msg_type" : "success"})

            if lifecycle_state == DesignacionesStates.pendiente_validacion_rrhh:
                fil.change_life_cycle_state(DesignacionesStates.pendiente_firma_otp) 
                op_send_by_email.run(
                    uuid,
                    notifications_template='designaciones_notificacion_pendiente_firma',
                    send_to_groups='Vicerrector Administrativo'
                ) 
                return logger.exit({"msg" : f"Las Designaciones Docente con UUID: {uuid} fue aprobada exitosamente", "msg_type" : "success"})
            
        except FileNotFoundError as e:
            flogger.error(f'Error al procesar el archivo: {str(e)}')
            return logger.exit(HttpResponse(
            str(e), 
            status='404'
        ), exc_info=True)        
        except AthentoseError as e:
            flogger.error(f'Error en la operación: {str(e)}')
            return logger.exit(HttpResponse(
                str(e), 
                status='400'
            ), exc_info=True)
        except Exception as e:
            flogger.error(f'Error inesperado: {str(e)}')
            return logger.exit(HttpResponse(
                str(e), 
                status='500'
            ), exc_info=True)
    
VERSION = ApruebaDesignaciones.version
NAME = ApruebaDesignaciones.name
DESCRIPTION = ApruebaDesignaciones.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = ApruebaDesignaciones.configuration_parameters

def run(uuid=None, **params):
    return ApruebaDesignaciones(uuid, **params).run()