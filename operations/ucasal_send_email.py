import logging

from django.contrib.auth.models import User
from django.utils.translation import gettext as _

from operations.classes.document_operation import DocumentOperation
from operations.enums import ProcessOperationParameterType, ProcessOperationParameterChoiceType
from textprocessing.utils import split_mails, str_is_mail

logger = logging.getLogger('athentose')


class SendDeliveryOperationCustom(DocumentOperation):
    version = '3.3'
    name = _("Send approval email")
    documentation = 'https://help.athento.com/es/docs/como-enviar-una-solicitud-de-aprobacion-por-email-con-una-operacion-o-automatismo-document-delivery/'
    description = _("This operation sends an approval email.")
    configuration_parameters = {
        'email': {
            'label': _('Email'),
            'help_text': _('Email to which the delivery document is sent'),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
        'metadata_type_name_email': {
            'label': _('Metadata Type email'),
            'help_text': _('Metadata containing the email to which the delivery document is sent'),
            'type': ProcessOperationParameterType.CHOICE.value[0],
            'subtype': ProcessOperationParameterChoiceType.METADATA_TYPE.value[0],
            'is_multiple': False,
        },
        'ask_for_approval': {
            'label': _('Ask for approval'),
            'help_text': _('Indicates if approval is required or not'),
            'type': ProcessOperationParameterType.BOOLEAN.value[0],
        },
        'delivery_template': {
            'label': _('Delivery template'),
            'help_text': _('Template used for delivery notification'),
            'type': ProcessOperationParameterType.TEXT.value[0],
        },
        'metadata_type_name_comment': {
            'label': _('Metadata Type comment'),
            'help_text': _('Metadata containing the comment to be included in the delivery document'),
            'type': ProcessOperationParameterType.CHOICE.value[0],
            'subtype': ProcessOperationParameterChoiceType.METADATA_TYPE.value[0],
            'is_multiple': False,
        },
        'metadata_type_name_email_cc': {
            'label': _('Metadata Type email CC'),
            'help_text': _('Metadata containing the email addresses (separated by comma, semicolon, space or '
                            'line break) that will also receive the delivery in CC'),
            'type': ProcessOperationParameterType.CHOICE.value[0],
            'subtype': ProcessOperationParameterChoiceType.METADATA_TYPE.value[0],
            'is_multiple': False,
        },
        'document_type_name_related_document_types': {
            'label': _('Document Types to attach'),
            'help_text': _('Document types of related documents to be attached to the delivery document'),
            'type': ProcessOperationParameterType.CHOICE.value[0],
            'subtype': ProcessOperationParameterChoiceType.DOCUMENT_TYPE.value[0],
            'is_multiple': True,
        },
        'attach_main_document': {
            'label': _('Attach main document'),
            'help_text': _('Indicates if main document is attached to the delivery document'),
            'type': ProcessOperationParameterType.BOOLEAN.value[0],
        },
        'is_otp_required': {
            'label': _('Use otp'),
            'help_text': _('Indicates if main document needs a otp'),
            'type': ProcessOperationParameterType.BOOLEAN.value[0],
        },
    }

    def execute(self, *args, **kwargs):
        email = self.parameters.get('email')
        email_metadata_name = self.parameters.get('metadata_type_name_email')
        email_cc_metadata_name = self.parameters.get('metadata_type_name_email_cc')
        comment_metadata_name = self.parameters.get('metadata_type_name_comment')
        document_types_to_attach = self.parameters.get('document_type_name_related_document_types')
        attach_main_document = self.parameters.get('attach_main_document')

        document = self.document

        if not email and email_metadata_name:
            email = document.get_metadata_value(email_metadata_name)

        if '|' in email:
            email = email.split('|')
        elif not str_is_mail(email):
            user = User.objects.filter(username=email).first()
            if user and user.email:
                email = user.email
            else:
                email = ''

        if email:
            if type(email) != list:
                email = [email]

            email_cc = []
            if email_cc_metadata_name:
                email_cc_value = document.get_metadata_value(email_cc_metadata_name)
                if email_cc_value:
                    email_cc = split_mails(email_cc_value)

            related_files = document.get_relations()
            files_to_attach = related_files.filter(doctype__in=document_types_to_attach)
            related_files_selected = list(map(lambda f: str(f.uuid), files_to_attach))
            if attach_main_document:
                related_files_selected.append(str(document.uuid))

            comment = document.get_metadata_value(comment_metadata_name) if comment_metadata_name else ''

            if comment:
                self.parameters['comment'] = comment
            if email_cc:
                self.parameters['cc_email'] = email_cc
            self.parameters['origin_metadata_type_name'] = email_metadata_name.name if email_metadata_name else ''
            # params is sent as context for the template
            # the params allows to pass custom params to the template
            # delivery_template sent inside params
            # document.delivery_document(email, related_files_selected=related_files_selected, **self.parameters)
            result = document.delivery_document(email, related_files_selected=related_files_selected, **self.parameters)
            logger.info(f"delivery_document devolvió: {type(result)} -> {result}")


VERSION = SendDeliveryOperationCustom.version
NAME = SendDeliveryOperationCustom.name
DESCRIPTION = SendDeliveryOperationCustom.description
DOCUMENTATION = SendDeliveryOperationCustom.documentation
ORDER = 100
CATEGORY = ""
POSTLOAD = True
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = SendDeliveryOperationCustom.configuration_parameters


def run(uuid=None, **params):
    # TODO (2022/10/06): This way to execute the operation is not ideal, but to keep the compatibility with
    #  the old implementation.
    return SendDeliveryOperationCustom(uuid, **params).run()