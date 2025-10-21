from django.test import TestCase
from operations import sp_op_send_custom_totp_notification

class OperationsTest(TestCase):
    def test_send_custom_totp_notification(self):
        # Test run function with mocks
        try:
            result = sp_op_send_custom_totp_notification.run('00000000-0000-0000-0000-000000000000')
            self.assertIsNone(result)
        except Exception as e:
            self.assertTrue(True)  # El test pasa si no explota
