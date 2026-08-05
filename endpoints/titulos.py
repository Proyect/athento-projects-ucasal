# -*- coding: utf-8 -*-
from django.urls import re_path as url
from django.http import HttpResponse
from file.models import File
from core.exceptions import AthentoseError
from ucasal2.utils import (
    default_permissions,
    traceback_ret,
    encodeJSON,
    getJsonBody,
    METHOD_NOT_ALLOWED,
    TituloStates,
    UcasalConfig,
)
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from file.foperations import op_send_by_email
from datetime import datetime


@default_permissions
@traceback_ret
def bfaresponse(request, uuid):
    """Recibe la respuesta de Blockchain (BFA) para un Título."""
    fil = None
    flogger = NullSpFeatureLogger()
    logger = SpLogger("athentose", "titulos.bfaresponse")
    try:
        logger.entry()

        if request.method != 'POST':
            return logger.exit(METHOD_NOT_ALLOWED)

        body = getJsonBody(request)
        result = body.get('status')
        if result not in ['success', 'failure']:
            raise AthentoseError(
                f"'status' debe ser 'success' o 'failure', en lugar de {result}"
            )

        fil = File.objects.get(uuid=uuid)

        flogger = SpFeatureLogger.getLogger(fil)
        fil.set_feature('bfa.response', body)

        # El padre del flujo de títulos debe tener este doctype
        if fil.doctype.name != 'titulo':
            raise AthentoseError(
                f"El documento con uuid '{uuid}' es de tipo '{fil.doctype.label}' "
                "en lugar de 'titulo'"
            )

        # Validar estado de ciclo de vida
        valid_states = [
            TituloStates.pendiente_blockchain,
            TituloStates.fallo_blockchain,
        ]
        if fil.life_cycle_state.name not in valid_states:
            raise AthentoseError(
                f"Sólo se puede registrar resultado de blockchain si está en "
                f"{valid_states}, pero está en '{fil.life_cycle_state.name}'"
            )

        fil.set_feature('bfa.result', encodeJSON(body))

        if result == 'success':
            fil.change_life_cycle_state(TituloStates.firmado)
            fil.set_feature('registro_blockchain', 'success')

            fecha_actual = datetime.now().strftime("%d/%m/%Y")

            op_send_by_email.run(
                uuid,
                notifications_template='titulos_notificacion_firmada',
                send_to_groups='SECRETARIA GRAL',
                fecha_firma=fecha_actual,
            )
            return logger.exit(
                HttpResponse("Resultado BFA registrado exitosamente")
            )
        else:
            fil.change_life_cycle_state(TituloStates.fallo_blockchain)
            op_send_by_email.run(
                uuid,
                notifications_template='titulos_notificacion_fallo_blockchain',
                send_to_groups='SISTEMAS',
            )
            return logger.exit(
                {
                    "msg": "Resultado BFA marcado como fallo en blockchain",
                    "msg_type": "error",
                }
            )

    except File.DoesNotExist:
        return logger.exit(
            HttpResponse("Título no encontrado", status=404), exc_info=True
        )
    except AthentoseError as e:
        return logger.exit(HttpResponse(str(e), status=400), exc_info=True)
    except Exception as e:
        return logger.exit(HttpResponse(str(e), status=500), exc_info=True)


# ================================
# Rutas
# ================================
routes = [
    url(
        r'^titulos/(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/bfaresponse/?$',
        bfaresponse,
    ),
]
