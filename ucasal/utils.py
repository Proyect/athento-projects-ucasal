from json import loads as decodeJSON, dumps as encodeJSON
import traceback


NoneType = type(None)
serializableJsonTypes = (int, str, float, bool, NoneType)


class TituloStates:
    pendiente_validacion_da = 'Pendiente de validacion DA (direccion de alumnos)'
    pendiente_validacion_fd = 'Pendiente de validacion FD (firma del decano)'
    pendiente_validacion_fr = 'Pendiente de validacion FR (firma del rector)'
    pendiente_validacion_tit = 'Pendiente de Validacion TIT (titulo)'
    pendiente_validacion_fsg = 'Pendiente de validacion FSG (secretaria general)'
    pendiente_firma_otp = 'Pendiente de Firma OTP'
    pendiente_blockchain = 'Pendiente Blockchain'
    fallo_blockchain = 'Fallo en Blockchain'
    firmado = 'Firmado'
    rechazado = 'RECHAZADO'


TITULO_TRANSITIONS_ALLOWED = {
    TituloStates.pendiente_validacion_da: [
        TituloStates.pendiente_validacion_fd,
        TituloStates.rechazado,
    ],
    TituloStates.pendiente_validacion_fd: [
        TituloStates.pendiente_validacion_fr,
        TituloStates.rechazado,
    ],
    TituloStates.pendiente_validacion_fr: [
        TituloStates.pendiente_validacion_tit,
        TituloStates.rechazado,
    ],
    TituloStates.pendiente_validacion_tit: [
        TituloStates.pendiente_validacion_fsg,
        TituloStates.rechazado,
    ],
    TituloStates.pendiente_validacion_fsg: [
        TituloStates.pendiente_firma_otp,
        TituloStates.rechazado,
    ],
    TituloStates.pendiente_firma_otp: [
        TituloStates.pendiente_blockchain,
        TituloStates.rechazado,
    ],
    TituloStates.pendiente_blockchain: [
        TituloStates.fallo_blockchain,
        TituloStates.firmado,
    ],
    TituloStates.fallo_blockchain: [],
    TituloStates.firmado: [],
    TituloStates.rechazado: [],
}


TITULO_ESTADO_CODIGO = {
    TituloStates.pendiente_validacion_da: 0,
    TituloStates.pendiente_validacion_fd: 1,
    TituloStates.pendiente_validacion_fr: 2,
    TituloStates.pendiente_validacion_tit: 3,
    TituloStates.pendiente_validacion_fsg: 4,
    TituloStates.pendiente_firma_otp: 5,
    TituloStates.pendiente_blockchain: 6,
    TituloStates.fallo_blockchain: 7,
    TituloStates.firmado: 8,
    TituloStates.rechazado: 99,
}


def can_transition(from_state: str, to_state: str) -> bool:
    options = TITULO_TRANSITIONS_ALLOWED.get(from_state) or []
    return to_state in options


class AthentoseError(Exception):
    pass


def getJsonBody(request):
    try:
        return decodeJSON(request.data) if type(request.data) != dict else request.data
    except Exception:
        raise AthentoseError('Error parseando el request body JSON string:\r\n' + traceback.format_exc())


def getJsonOrStr(something):
    try:
        return decodeJSON(something) if type(something) != dict else str(something)
    except Exception:
        return str(something)


def traceback_ret(func):
    """Wrapper simple que captura excepciones y devuelve JSON.

    Se define sin depender directamente de HttpResponse para que este módulo
    pueda importarse incluso fuera de Django (por ejemplo en scripts de prueba).
    Las vistas que quieran usar este decorador deberían redefinir una versión
    específica que utilice HttpResponse dentro de un entorno Django configurado.
    """

    def f(request, *args, **kargs):
        try:
            return func(request, *args, **kargs)
        except Exception:
            # Retorna un dict con información del error; la vista puede
            # transformarlo en HttpResponse según corresponda.
            return {
                'request': {
                    'method': getattr(request, 'method', ''),
                    'params': getattr(request, 'GET', {}),
                },
                'error': traceback.format_exc(),
            }

    return f
