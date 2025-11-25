# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from operations.enums import ProcessOperationParameterType, ProcessOperationParameterChoiceType
from core.exceptions import AthentoseError
from notifications.models import NotificationTemplate
from django.utils.translation import gettext as _
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger

from ucasal.utils import titulo_doctype_name, TituloStates


class UcasalTituloNotificarCambioEstado(DocumentOperation):
    version = "1.0"
    name = _("Notificar cambio de estado de título")
    description = _("Notifica por email cuando un título cambia de estado. Determina el destinatario según el estado.")
    configuration_parameters = {
        'notifications_template': {
            'label': _("Notification template"),
            'help_text': _("Write the name of the notification template (e.g., ucasal_titulo_estado_cambiado)."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
        'estado_anterior': {
            'label': _("Previous state"),
            'help_text': _("Previous state of the title (optional)."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
        'estado_nuevo': {
            'label': _("New state"),
            'help_text': _("New state of the title (optional, will use current state if not provided)."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
        'observaciones': {
            'label': _("Observations"),
            'help_text': _("Additional observations about the state change (optional)."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
    }
    _logger: SpLogger = SpLogger("athentose", "UcasalTituloNotificarCambioEstado")

    def __init__(self, document=None, **params):
        super().__init__(document=document, **params)
        # Convertir params a parameters para compatibilidad
        self.parameters = self.params

    def execute(self, *args, **kwargs):
        try:
            logger = self._logger
            logger.entry(additional_info={"self.parameters": self.parameters})
            print('ucasal_titulo_notificar_cambio_estado.execute() - ENTER')
            uuid = 'N/A'
            fil = self.document
            uuid = str(fil.uuid)

            # Verificar doctype
            if fil.doctype.name != titulo_doctype_name:
                logger.debug(
                    f"Documento '{uuid}' no es un título (doctype: {fil.doctype.name}), saltando..."
                )
                return {
                    'msg_type': 'info',
                    'msg': f'Documento no es un título (doctype: {fil.doctype.name})'
                }

            # Leer parámetros
            notifications_template = self.parameters.get('notifications_template', '')
            if notifications_template.strip() == '':
                raise AthentoseError(
                    _("Argument notifications_template must be a non-empty string instead of '%s'") 
                    % notifications_template
                )

            estado_anterior = self.parameters.get('estado_anterior', '')
            estado_nuevo = self.parameters.get('estado_nuevo', '')
            if not estado_nuevo:
                estado_nuevo = fil.life_cycle_state.name if fil.life_cycle_state else fil.life_cycle_state_legacy
            observaciones = self.parameters.get('observaciones', '')

            # Determinar destinatario según el estado nuevo
            send_to = self._determinar_destinatario(fil, estado_nuevo)
            
            if not send_to or '@' not in send_to:
                logger.warning(f"No se pudo determinar destinatario para título {uuid} en estado {estado_nuevo}")
                return {
                    'msg_type': 'warning',
                    'msg': f'No se pudo determinar destinatario para notificación'
                }

            # Construir contexto para el template
            context = {
                'fil': fil,
                'estado_anterior': estado_anterior,
                'estado_nuevo': estado_nuevo,
            }
            if observaciones:
                context['observaciones'] = observaciones

            # Enviar notificación
            self._send_notification(
                email=send_to,
                notification_template_name=notifications_template,
                context=context
            )

            print('ucasal_titulo_notificar_cambio_estado.execute() - EXIT')
            return logger.exit({
                'msg_type': 'success',
                'msg': f'Notificación enviada a {send_to}',
            })
        except AthentoseError as error:
            logger.error(f"Error notificando cambio de estado del título '{uuid}': {str(error)}", exc_info=True)
            print(f"Error notificando cambio de estado del título '{uuid}': {str(error)}")
            return logger.exit({
                'msg_type': 'error',
                'msg': f'Error enviando notificación: {error}'
            },
            'Error enviando notificación de cambio de estado',
            additional_info={"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
            exc_info=True
            )
        except Exception as error:
            print(f"Error inesperado notificando cambio de estado del título '{uuid}': {error}")
            logger.error(f"Error inesperado notificando cambio de estado del título '{uuid}': {error}", exc_info=True)
            print('ucasal_titulo_notificar_cambio_estado.execute() - EXIT - With error')
            return logger.exit({
                'msg_type': 'error',
                'msg': 'Error inesperado enviando notificación'
            },
            'Error inesperado enviando notificación',
            additional_info={"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
            exc_info=True
            )

    def _determinar_destinatario(self, fil, estado_nuevo):
        """
        Determina el email del destinatario según el estado del título.
        
        Mapeo de estados a destinatarios:
        - Pendiente Aprobación UA -> metadata.titulo_email_ua
        - Pendiente Aprobación R -> metadata.titulo_email_rector
        - Pendiente Firma SG -> metadata.titulo_email_sg
        - Otros estados -> metadata.titulo_email_ua (por defecto)
        """
        logger = self._logger
        
        # Mapeo de estados a metadata keys de email
        estado_email_map = {
            TituloStates.pendiente_aprobacion_ua: 'metadata.titulo_email_ua',
            TituloStates.aprobado_ua: 'metadata.titulo_email_ua',
            TituloStates.pendiente_aprobacion_r: 'metadata.titulo_email_rector',
            TituloStates.aprobado_r: 'metadata.titulo_email_rector',
            TituloStates.pendiente_firma_sg: 'metadata.titulo_email_sg',
            TituloStates.firmado_sg: 'metadata.titulo_email_sg',
            TituloStates.titulo_emitido: 'metadata.titulo_email_sg',
        }
        
        # Obtener metadata key según estado
        email_metadata_key = estado_email_map.get(estado_nuevo, 'metadata.titulo_email_ua')
        
        # Intentar obtener email desde metadata
        try:
            email = fil.gmv(email_metadata_key)
            if email and '@' in str(email):
                logger.debug(f"Email obtenido desde {email_metadata_key}: {email}")
                return str(email)
        except Exception as e:
            logger.debug(f"No se pudo obtener email desde {email_metadata_key}: {e}")
        
        # Si no se encontró, intentar email genérico
        try:
            email = fil.gmv('metadata.titulo_email')
            if email and '@' in str(email):
                logger.debug(f"Email obtenido desde metadata.titulo_email: {email}")
                return str(email)
        except Exception as e:
            logger.debug(f"No se pudo obtener email desde metadata.titulo_email: {e}")
        
        return None

    def _send_notification(self, email=None, notification_template_name=None, context={}):
        logger = self._logger
        logger.entry()
        NotificationTemplate.objects.send(
            template_name=notification_template_name,
            to=[email],
            context=context
        )
        logger.exit()


VERSION = UcasalTituloNotificarCambioEstado.version
NAME = UcasalTituloNotificarCambioEstado.name
DESCRIPTION = UcasalTituloNotificarCambioEstado.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = UcasalTituloNotificarCambioEstado.configuration_parameters


def run(uuid=None, **params):
    return UcasalTituloNotificarCambioEstado(uuid, **params).run()

