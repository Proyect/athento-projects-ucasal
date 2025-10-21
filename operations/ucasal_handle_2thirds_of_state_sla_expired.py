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



class Handle2ThirdsOfStateSlaExpiredOperation(DocumentOperation):
    version = "1.0"
    name = _("Lifecycle state sla nearly expired handler")
    description = _("Called when the current form has 2/3 of its current lifecycle state sla expiration time elapsed.")
    configuration_parameters = {    
        'send_to': {
            'label': _("Send to"),
            'help_text': _("Write the email or a metadata name containing an email."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
        'notifications_template': {
            'label': _("Notification template"),
            'help_text': _("Write the name of the notification template."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
    }
    
    def execute(self, *args, **kwargs):
        try:
            logger = SpLogger("athentose", "Handle2ThirdsOfStateSlaExpiredOperation")
            print('ucasal_handle_2thirds_of_state_sla_expired.execute() - ENTER')
            logger.entry(additional_info={"self.parameters": self.parameters})
            uuid = 'N/A'
            fil = self.document
            uuid = str(fil.uuid)


            # Read the parameters
            send_to = self.parameters.get('send_to')
            notifications_template = self.parameters.get('notifications_template')

            print('Parameters: ' + str({
                'send_to': send_to, 
                'notifications_template': notifications_template, 
              })
            )

            # Check current status sla
            current_state = fil.life_cycle_state
            max_minutes = current_state.maximum_time
            if not max_minutes:
                raise AthentoseError(_(f"Current state '{current_state.name}' of form '{fil.doctype.label}' ({uuid}) does not have a state sla specified.'"))

            # Calculate time to expitarion
            current_state_date = fil.life_cycle_state_date
            now = datetime.now(current_state_date.tzinfo)
            elapsed_time = now - current_state_date
            elapsed_minutes = elapsed_time.total_seconds() / 60
            remaining_minutes = max_minutes - elapsed_minutes

            #if math.trunc(remaining_minutes) <= 0:
            #    raise AthentoseError(_(f"Operation ucasal_handle_2thirds_of_state_sla_expired shouldn't have been called on form '{fil.doctype.name}' ({uuid}) because the current state '{{current_state.name}}' SLA has already expired."))
            
            elapsed_time_str = self._format_minutes(elapsed_minutes)
            remaining_time_str = self._format_minutes(remaining_minutes)

            print(f'elapsed_time_str: {elapsed_time_str}')
            print(f'remaining_time_str: {remaining_time_str}')
            logger.debug(f'elapsed_time_str: {elapsed_time_str}')
            logger.debug(f'remaining_time_str: {remaining_time_str}')

            # This tells the template not to show the elapsed time message
            if elapsed_minutes < 5:
                elapsed_time_str = ''

            # Send notification email
            sender = PublicLinkSender(
                uuid=str(self.document.uuid), 
                mail_to=send_to,
                phone_number='+5491155555555',
                notification_template_name= notifications_template,
                notification_template_context={
                    'elapsed_time': elapsed_time_str
                },
                link_type='edit',
                expiration_days=0
            )

            sender.send_by_email()

            print('ucasal_handle_2thirds_of_state_sla_expired.execute() - EXIT')

            return logger.exit({
              'msg_type': 'success',
              'msg': 'Se ha notificado al firmante',
            })
        except AthentoseError as error:
            logger.error(f"Error enviando link público al firmante. Error:  {str(error)}", exc_info=True)
            logger.debug('ucasal_handle_2thirds_of_state_sla_expired.execute() - EXIT - With error')
            return logger.exit( {
                  'msg_type': 'error',
                  'msg': f'Error enviando link público al firmante: {error}'
                },
                additional_info= {"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
                exc_info=True  
            )           
        except Exception as error:
            print(f"Error inesperado enviando link público al firmante del form '{fil.doctype.label}' ({uuid}).\r\n {error}")
            logger.error(f"Error inesperado enviando link público al firmante del form '{fil.doctype.label}' ({uuid}).\r\n {error}", exc_info=True)
            print('ucasal_handle_2thirds_of_state_sla_expired.execute() - EXIT - With error')
            return logger.exit({
                  'msg_type': 'error',
                  'msg': 'Error inesperado enviando link público al firmante'
                },
                additional_info= {"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
                exc_info=True  
            )      

    def _format_minutes(self, minutes):
        days = minutes / 60 / 24
        days_int = math.trunc(days)

        hours = (days - days_int) * 24
        hours_int = math.trunc(hours)

        minutes = (hours - hours_int) * 60
        minutes_int = math.trunc(minutes)

        time_str = f'{days_int}d {hours_int}h {minutes_int}m'
        return time_str



VERSION = Handle2ThirdsOfStateSlaExpiredOperation.version
NAME = Handle2ThirdsOfStateSlaExpiredOperation.name
DESCRIPTION = Handle2ThirdsOfStateSlaExpiredOperation.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = Handle2ThirdsOfStateSlaExpiredOperation.configuration_parameters


def run(uuid=None, **params):
    return Handle2ThirdsOfStateSlaExpiredOperation(uuid, **params).run()