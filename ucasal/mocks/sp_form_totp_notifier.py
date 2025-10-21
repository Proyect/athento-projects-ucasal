class SpFormTotpNotifier:
    @staticmethod
    def send_otp_notification(uuid, send_to, notification_template_name, otp_validity_seconds):
        return {
            'send_to': send_to,
            'otp': '123456',
            'expiration': 9999999999
        }
