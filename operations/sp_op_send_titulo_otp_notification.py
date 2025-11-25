# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from operations.enums import ProcessOperationParameterType, ProcessOperationParameterChoiceType
from core.exceptions import AthentoseError
from notifications.models import NotificationTemplate
from sp_totp_generator import TOTPGenerator
from django.utils.translation import gettext as _
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger
from ucasal.utils import get_totp_key, titulo_doctype_name


class SpSendTituloOtpNotification(DocumentOperation):
    version = "1.0"
    name = _("Send TOTP Notification for Title")
    description = _("Generates a TOTP code for the current title and notifies the user by email")
    configuration_parameters = {
        'send_to': {
            'label': _("Send to"),
            'help_text': _("Write the email or a metadata name containing an email."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
        'notifications_template': {
            'label': _("Notification template"),
            'help_text': _("Write the name of the notification template (e.g., ucasal_titulo_otp_notification)."),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
        'otp_validity_seconds': {
            'label': _("OTP validity period"),
            'help_text': _("Maximum interval to validate the OTP (in seconds)"),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
    }
    _logger: SpLogger = SpLogger("athentose", "SpSendTituloOtpNotification")

    def __init__(self, document=None, **params):
        super().__init__(document=document, **params)
        # Convertir params a parameters para compatibilidad
        self.parameters = self.params

    def execute(self, *args, **kwargs):
        try:
            logger = self._logger
            logger.entry(additional_info={"self.parameters": self.parameters})
            print('sp_op_send_titulo_otp_notification.execute() - ENTER')
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

            send_to = self.parameters.get('send_to', '')
            # Obtener email desde metadata si es necesario
            if 'metadata.' in send_to:
                send_to = str(fil.gmv(send_to))

            if not send_to or '@' not in send_to:
                raise AthentoseError(
                    _("Argument send_to must be either an email address or a metadata name instead of '%s'") 
                    % send_to
                )

            # Obtener período de validez del OTP en segundos
            otp_validity_seconds = self.parameters.get('otp_validity_seconds', '')
            if not otp_validity_seconds.isdigit():
                raise AthentoseError(
                    _(f"Argument otp_validity_seconds must be an integer instead of '{otp_validity_seconds}'")
                )
            otp_validity_seconds = int(otp_validity_seconds)

            # Generar OTP y enviarlo
            otp_generator = TOTPGenerator(get_totp_key(uuid), token_validity_seconds=otp_validity_seconds)
            otp_code = otp_generator.generate_token()['code']
            
            self._send_notification(
                send_to,
                notification_template_name=notifications_template,
                context={'fil': fil, 'otp': otp_code}
            )

            print('sp_op_send_titulo_otp_notification.execute() - EXIT')

            return logger.exit({
                'msg_type': 'success',
                'msg': f'Se ha enviado el código OTP a {send_to}',
            })
        except AthentoseError as error:
            print(f"Error enviando el código OTP para título '{uuid}': {error}")
            return logger.exit({
                'msg_type': 'error',
                'msg': f'Error enviando el código OTP: {error}'
            },
            'Error enviando el código OTP',
            additional_info={"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
            exc_info=True
            )
        except Exception as error:
            print(f"Error inesperado enviando código OTP para título '{uuid}': {error}")
            print('sp_op_send_titulo_otp_notification.execute() - EXIT - With error')
            return logger.exit({
                'msg_type': 'error',
                'msg': 'Error inesperado enviando el código OTP'
            },
            'Error inesperado enviando el código OTP',
            additional_info={"doctype": fil.doctype.label, "doctitle": fil.filename, "uuid": uuid},
            exc_info=True
            )

    def _send_notification(self, email=None, notification_template_name=None, context={}):
        logger = self._logger
        logger.entry()
        NotificationTemplate.objects.send(
            template_name=notification_template_name,
            to=[email],
            context=context
        )
        logger.exit()


VERSION = SpSendTituloOtpNotification.version
NAME = SpSendTituloOtpNotification.name
DESCRIPTION = SpSendTituloOtpNotification.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = SpSendTituloOtpNotification.configuration_parameters


def run(uuid=None, **params):
    return SpSendTituloOtpNotification(uuid, **params).run()

