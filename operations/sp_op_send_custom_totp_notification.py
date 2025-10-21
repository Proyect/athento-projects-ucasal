# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from operations.enums import ProcessOperationParameterType, ProcessOperationParameterChoiceType
from core.exceptions import AthentoseError
from notifications.models import NotificationTemplate
from sp_totp_generator import TOTPGenerator
from django.utils.translation import gettext as _
from sp_logger import SpLogger
from ucasal.utils import get_totp_key


class SpSendCustopTotpNotification(DocumentOperation):
    version = "1.0"
    name = _("Send custom TOTP Notification")
    description = _("Generates a TOPT code for the current document and notifies the user by email")
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
        'otp_validity_seconds': {
            'label': _("OTP validity period"),
            'help_text': _("Maximum interval to validate the OTP (in seconds)"),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },        
    }
    _logger:SpLogger = SpLogger("athentose", "SpSendCustopTotpNotification")
    def execute(self, *args, **kwargs):
        try:
            logger = self._logger
            logger.entry(additional_info={"self.parameters": self.parameters})
            print('sp_op_send_custom_totp_notification.execute() - ENTER')
            uuid = 'N/A'
            fil = self.document
            uuid = str(fil.uuid)

            # Read the parameters
            notifications_template = self.parameters.get('notifications_template', '')
            if notifications_template.strip() == '':
                raise AthentoseError(_("Argument notifications_template must be a non-empty string instead of '%s'") % notifications_template)

            send_to = self.parameters.get('send_to', '')
            # Get the email #TODO: improve email format validation
            if('metadata.' in send_to):
                send_to = str(fil.gmv(send_to))

            if '@' not in send_to:
                raise AthentoseError(_("Argument mail_to must be either an email address or a metadata name instead of '%s'") % send_to)

            # Get the OTP validity interval in seconds
            otp_validity_seconds = self.parameters.get('otp_validity_seconds', '')
            if not otp_validity_seconds.isdigit():
                raise AthentoseError(_(f"Argument otp_validity_seconds must be an integer instead of '{otp_validity_seconds}'")) 
            otp_validity_seconds = int(otp_validity_seconds)

            # Generate the OTP and send it
            otp_generator = TOTPGenerator(get_totp_key(uuid), token_validity_seconds=otp_validity_seconds)
            otp_code = otp_generator.generate_token()['code']
            self._send_notification(send_to, notification_template_name=notifications_template, context={'fil': fil, 'otp': otp_code} )

            print('sp_op_send_custom_totp_notification.execute() - EXIT')

            return logger.exit({
              'msg_type': 'success',
              'msg': 'Se ha enviado el código OTP al firmante',
            })
        except AthentoseError as error:
            print(f"Error enviando el código OTP al firmante del form '{fil.doctype.label}' ({uuid}): {error}")
            return logger.exit(
                {
                  'msg_type': 'error',
                  'msg': f'Error enviando el código OTP al firmante: {error}'
                }, 
                'Error enviando el código OTP al firmante',
                additional_info= {"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
                exc_info=True
            )
        except Exception as error:
            print(f"Error inesperado notificando al firmante del form '{fil.doctype.label}' ({uuid}): {error}")
           
            print('sp_op_send_custom_totp_notification.execute() - EXIT - With error')
            return logger.exit({
                  'msg_type': 'error',
                  'msg': 'Error inesperado enviando el código OTP al firmante'
                },
                'Error inesperado enviando el código OTP al firmante',
                additional_info= {"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
                exc_info=True
            )

    def _send_notification(self, email=None, notification_template_name=None, context={}):
        logger = self._logger
        logger.entry()
        NotificationTemplate.objects.send(template_name=notification_template_name, to=[email],
                                          context=context)   
        logger.exit()

VERSION = SpSendCustopTotpNotification.version
NAME = SpSendCustopTotpNotification.name
DESCRIPTION = SpSendCustopTotpNotification.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = SpSendCustopTotpNotification.configuration_parameters


def run(uuid=None, **params):
    return SpSendCustopTotpNotification(uuid, **params).run()