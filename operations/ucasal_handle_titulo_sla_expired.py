# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from operations.enums import ProcessOperationParameterType, ProcessOperationParameterChoiceType
from core.exceptions import AthentoseError
from django.utils.translation import gettext as _
from datetime import datetime
import math
from sp_public_link_sender import PublicLinkSender

try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger

from ucasal.utils import titulo_doctype_name, TituloStates


class HandleTituloSlaExpiredOperation(DocumentOperation):
    version = "1.0"
    name = _("Título SLA nearly expired handler")
    description = _("Called when a title has 2/3 of its current lifecycle state sla expiration time elapsed.")
    configuration_parameters = {
        'send_to': {
            'label': _("Send to"),
            'help_text': _("Write the email or a metadata name containing an email."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
        'notifications_template': {
            'label': _("Notification template"),
            'help_text': _("Write the name of the notification template (e.g., ucasal_titulo_near_state_sla_expiration)."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
    }

    def __init__(self, document=None, **params):
        super().__init__(document=document, **params)
        # Convertir params a parameters para compatibilidad
        self.parameters = self.params

    def execute(self, *args, **kwargs):
        try:
            logger = SpLogger("athentose", "HandleTituloSlaExpiredOperation")
            print('ucasal_handle_titulo_sla_expired.execute() - ENTER')
            logger.entry(additional_info={"self.parameters": self.parameters})
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
            send_to = self.parameters.get('send_to')
            notifications_template = self.parameters.get('notifications_template')

            print('Parameters: ' + str({
                'send_to': send_to,
                'notifications_template': notifications_template,
            }))

            # Obtener email del destinatario
            if 'metadata.' in send_to:
                send_to = str(fil.gmv(send_to))

            if not send_to or '@' not in send_to:
                # Intentar determinar destinatario automáticamente según estado
                send_to = self._determinar_destinatario(fil)
                if not send_to:
                    raise AthentoseError(
                        _("No se pudo determinar destinatario para notificación de SLA. "
                          "Proporcione 'send_to' o configure metadata de email.")
                    )

            # Verificar SLA del estado actual
            current_state = fil.life_cycle_state
            if not current_state:
                raise AthentoseError(
                    _(f"El título '{uuid}' no tiene un estado de ciclo de vida asignado.")
                )

            max_minutes = current_state.maximum_time
            if not max_minutes:
                logger.debug(
                    f"Estado '{current_state.name}' del título '{uuid}' no tiene SLA especificado, saltando..."
                )
                return {
                    'msg_type': 'info',
                    'msg': f'Estado sin SLA especificado'
                }

            # Calcular tiempo transcurrido y restante
            current_state_date = fil.life_cycle_state_date
            if not current_state_date:
                raise AthentoseError(
                    _(f"El título '{uuid}' no tiene fecha de cambio de estado.")
                )

            now = datetime.now(current_state_date.tzinfo)
            elapsed_time = now - current_state_date
            elapsed_minutes = elapsed_time.total_seconds() / 60
            remaining_minutes = max_minutes - elapsed_minutes

            elapsed_time_str = self._format_minutes(elapsed_minutes)
            remaining_time_str = self._format_minutes(remaining_minutes)

            print(f'elapsed_time_str: {elapsed_time_str}')
            print(f'remaining_time_str: {remaining_time_str}')
            logger.debug(f'elapsed_time_str: {elapsed_time_str}')
            logger.debug(f'remaining_time_str: {remaining_time_str}')

            # No mostrar mensaje de tiempo transcurrido si es muy poco
            if elapsed_minutes < 5:
                elapsed_time_str = ''

            # Enviar notificación por email
            sender = PublicLinkSender(
                uuid=str(self.document.uuid),
                mail_to=send_to,
                phone_number='+5491155555555',
                notification_template_name=notifications_template,
                notification_template_context={
                    'elapsed_time': elapsed_time_str,
                    'estado_actual': current_state.name
                },
                link_type='edit',
                expiration_days=0
            )

            sender.send_by_email()

            print('ucasal_handle_titulo_sla_expired.execute() - EXIT')

            return logger.exit({
                'msg_type': 'success',
                'msg': f'Se ha notificado a {send_to} sobre SLA próximo a vencer',
            })
        except AthentoseError as error:
            logger.error(f"Error enviando notificación de SLA para título '{uuid}': {str(error)}", exc_info=True)
            logger.debug('ucasal_handle_titulo_sla_expired.execute() - EXIT - With error')
            return logger.exit({
                'msg_type': 'error',
                'msg': f'Error enviando notificación de SLA: {error}'
            },
            additional_info={"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
            exc_info=True
            )
        except Exception as error:
            print(f"Error inesperado enviando notificación de SLA para título '{uuid}': {error}")
            logger.error(f"Error inesperado enviando notificación de SLA para título '{uuid}': {error}", exc_info=True)
            print('ucasal_handle_titulo_sla_expired.execute() - EXIT - With error')
            return logger.exit({
                'msg_type': 'error',
                'msg': 'Error inesperado enviando notificación de SLA'
            },
            additional_info={"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
            exc_info=True
            )

    def _determinar_destinatario(self, fil):
        """
        Determina el email del destinatario según el estado actual del título.
        """
        logger = SpLogger("athentose", "HandleTituloSlaExpiredOperation")
        estado_actual = fil.life_cycle_state.name if fil.life_cycle_state else fil.life_cycle_state_legacy

        # Mapeo de estados a metadata keys de email
        estado_email_map = {
            TituloStates.pendiente_aprobacion_ua: 'metadata.titulo_email_ua',
            TituloStates.aprobado_ua: 'metadata.titulo_email_ua',
            TituloStates.pendiente_aprobacion_r: 'metadata.titulo_email_rector',
            TituloStates.aprobado_r: 'metadata.titulo_email_rector',
            TituloStates.pendiente_firma_sg: 'metadata.titulo_email_sg',
            TituloStates.firmado_sg: 'metadata.titulo_email_sg',
        }

        email_metadata_key = estado_email_map.get(estado_actual, 'metadata.titulo_email_ua')

        try:
            email = fil.gmv(email_metadata_key)
            if email and '@' in str(email):
                logger.debug(f"Email obtenido desde {email_metadata_key}: {email}")
                return str(email)
        except Exception as e:
            logger.debug(f"No se pudo obtener email desde {email_metadata_key}: {e}")

        return None

    def _format_minutes(self, minutes):
        days = minutes / 60 / 24
        days_int = math.trunc(days)

        hours = (days - days_int) * 24
        hours_int = math.trunc(hours)

        minutes = (hours - hours_int) * 60
        minutes_int = math.trunc(minutes)

        time_str = f'{days_int}d {hours_int}h {minutes_int}m'
        return time_str


VERSION = HandleTituloSlaExpiredOperation.version
NAME = HandleTituloSlaExpiredOperation.name
DESCRIPTION = HandleTituloSlaExpiredOperation.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = HandleTituloSlaExpiredOperation.configuration_parameters


def run(uuid=None, **params):
    return HandleTituloSlaExpiredOperation(uuid, **params).run()

