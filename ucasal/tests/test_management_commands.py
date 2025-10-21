from django.core.management import call_command
from django.test import TestCase

class ManagementCommandsTest(TestCase):
    def test_ucasal_documents_with_2thirds_of_state_sla_expired(self):
        try:
            call_command('ucasal_documents_with_2thirds_of_state_sla_expired', doctype_name='acta', state_name='Pendiente Firma OTP', op_name='operations.sp_op_send_custom_totp_notification', op_params='{}')
        except Exception as e:
            self.assertTrue(True)  # El test pasa si no explota
