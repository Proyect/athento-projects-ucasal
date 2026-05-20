from django.urls import re_path as url
from django.http import HttpResponse
from file.models import File
from core.exceptions import AthentoseError
from utils import (
    default_permissions,
    traceback_ret,
    encodeJSON,
    getJsonBody,
    METHOD_NOT_ALLOWED,
    DesignacionesStates,
    UcasalConfig
)
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from model.ucasal.exceptions import UcasalServiceError
from file.foperations import op_send_by_email
from external_services.ucasal.designaciones_services import DesignacionesServices
from external_services.ucasal.ucasal_services import UcasalServices
from datetime import datetime

@default_permissions
@traceback_ret
def bfaresponse(request, uuid):
    """ Recibe la respuesta de Blockchain (BFA) para una Designación """
    fil: File = None
    flogger: SpFeatureLogger = NullSpFeatureLogger()
    logger = SpLogger("athentose", "designaciones.bfaresponse")
    try:
        logger.entry()

        if request.method != 'POST':
            return logger.exit(METHOD_NOT_ALLOWED)

        body = getJsonBody(request)
        result = body.get('status')
        if result not in ['success', 'failure']:
            raise AthentoseError(f"'status' debe ser 'success' o 'failure', en lugar de {result}")

        # Buscar la designación
        fil = File.objects.get(uuid=uuid)
        if not fil:
            raise FileNotFoundError(f"La designación '{uuid}' no existe")

        flogger = SpFeatureLogger.getLogger(fil)
        fil.set_feature('bfa.response', body)

        # Validar tipo de documento
        if fil.doctype.name != 'designaciones':
            raise AthentoseError(
                f"El documento con uuid '{uuid}' es de tipo '{fil.doctype.label}' en lugar de 'designaciones'"
            )

        # Validar estado de ciclo de vida
        valid_states = [DesignacionesStates.pendiente_blockchain, DesignacionesStates.fallo_blockchain]
        if fil.life_cycle_state.name not in valid_states:
            raise AthentoseError(
                f"Sólo se puede registrar resultado de blockchain si está en {valid_states}, "
                f"pero está en '{fil.life_cycle_state.name}'"
            )

        # Guardar resultado
        fil.set_feature('bfa.result', encodeJSON(body))
        if result == 'success':
            fil.change_life_cycle_state(DesignacionesStates.firmado)
            fil.set_feature('registro_blockchain', result)
           
            auth_token = UcasalServices.get_auth_token(
                user=UcasalConfig.token_svc_user(),
                password=UcasalConfig.token_svc_password()
            )

            # Notificar a UCASAL que pasó a estado 5 (Firmado)
            response = DesignacionesServices.notify_blockchain_success(uuid, 5, auth_token)
            fil.set_feature('Response estado 5', response.text)
            fil.set_feature('Status Code 5', response.status_code)

            
            fecha_actual = datetime.now().strftime("%d/%m/%Y")

            op_send_by_email.run(
                uuid,
                notifications_template='designaciones_notificacion_firmada',
                send_to_groups='Legajo Docente',            
                fecha_firma=fecha_actual
            )  
            return logger.exit(HttpResponse("Resultado BFA registrado exitosamente"))
        else:
            fil.change_life_cycle_state(DesignacionesStates.fallo_blockchain)
            op_send_by_email.run(
                uuid,
                notifications_template='designaciones_notificacion_fallo_blockchain',
                send_to_groups='SISTEMAS'
            )  
            return logger.exit({"msg": "Resultado BFA marcado como fallo en blockchain", "msg_type": "error"})
    
    except File.DoesNotExist:
        return logger.exit(HttpResponse("Designación no encontrada", status=404), exc_info=True)
    except UcasalServiceError as e:
        flogger.error(f"Error notificando resultado blockchain: {e.detailed_message()}", 'bfaresponse', exc_info=True)
        if fil:
            # fil.set_metadata('metadata.designacion_error_servicio_externo', True, overwrite=True)
            fil.set_feature('error_servicio_externo', True)

            mail_params = {
                'send_to_groups': 'SISTEMAS',
                'notifications_template': 'ucasal2_error_in_ucasal_service_call_notification',
                'error': e.detailed_message(),
                'url': fil.get_url_file_view(),
            }
            op_send_by_email.run(uuid, **mail_params)
        return logger.exit(HttpResponse(str(e), status=500), exc_info=True, additional_info=e.to_dict())
    except AthentoseError as e:
        return logger.exit(HttpResponse(str(e), status=400), exc_info=True)
    except Exception as e:
        return logger.exit(HttpResponse(str(e), status=500), exc_info=True)


# ================================
# Rutas
# ================================
routes = [
    url(
        r'^designaciones/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/bfaresponse/?$',
        bfaresponse
    ),
]
