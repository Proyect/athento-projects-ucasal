from django.urls import re_path as url
from django.http import HttpResponse
from file.models import File
from core.exceptions import AthentoseError
from custom.ucasal2.utils import (
    default_permissions,
    traceback_ret,
    getJsonBody,
    ProgramasStates,
    UcasalConfig,
)
from custom.ucasal2.external_services.ucasal.ucasal_services import UcasalServices
from custom.ucasal2.external_services.ucasal.programas_services import ProgramasServices
from file.foperations import op_send_by_email

@default_permissions
@traceback_ret
def bfaresponse(request, uuid):
    if request.method != 'POST':
        from custom.ucasal2.utils import METHOD_NOT_ALLOWED
        return METHOD_NOT_ALLOWED

    body = getJsonBody(request)
    result = body.get('status')
    if result not in ['success', 'failure']:
        raise AthentoseError("'status' debe ser 'success' o 'failure'")

    fil = File.objects.get(uuid=uuid)
    if fil.doctype.name != 'programa':
        raise AthentoseError(f"No es un programa, es {fil.doctype.label}")

    if fil.life_cycle_state.name not in [ProgramasStates.pendiente_blockchain, ProgramasStates.fallo_blockchain]:
        raise AthentoseError("Estado inválido para recibir respuesta BFA")

    fil.set_feature('bfa.result', body)

    if result == 'success':
        fil.change_life_cycle_state(ProgramasStates.firmado)
        fil.set_metadata("estado", ProgramasStates.firmado, overwrite=True)
        fil.set_feature("registro_blockchain", "success")

        auth_token = UcasalServices.get_auth_token(
            user=UcasalConfig.token_svc_user(),
            password=UcasalConfig.token_svc_password()
        )
        ProgramasServices.notify_change_state(
            auth_token=auth_token,
            uuid=uuid,
            state=5,
        )

        op_send_by_email.run(
            uuid,
            notifications_template='programas_notificacion_firmada',
            send_to_groups='Docentes',
        )
        return HttpResponse("Resultado BFA registrado exitosamente")
    else:
        fil.change_life_cycle_state(ProgramasStates.fallo_blockchain)
        fil.set_metadata("estado", ProgramasStates.fallo_blockchain, overwrite=True)
        op_send_by_email.run(
            uuid,
            notifications_template='programas_notificacion_fallo_blockchain',
            send_to_groups='SISTEMAS',
        )
        return HttpResponse("Fallo en blockchain", status=500)

routes = [
    url(r'^programas/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/bfaresponse/?$', bfaresponse),
]