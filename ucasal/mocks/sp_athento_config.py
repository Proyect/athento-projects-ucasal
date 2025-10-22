class SpAthentoConfig:
    @staticmethod
    def get_str(key, is_secret=False):
        # Devolver URLs válidas para los endpoints
        if 'qr.url' in key:
            return "https://api.qrserver.com/v1/create-qr-code/"
        elif 'gettoken.url' in key:
            return "https://api.ucasal.edu.ar/token"
        elif 'stamps.url' in key:
            return "https://api.ucasal.edu.ar/stamps"
        elif 'change_acta.url' in key:
            return "https://api.ucasal.edu.ar/change-acta"
        elif 'acortar_url.url' in key:
            return "https://api.ucasal.edu.ar/shorten"
        elif 'validation_url_template' in key:
            return "https://ucasal.edu.ar/validar/{{uuid}}"
        elif 'otp.validation_url_template' in key:
            return "https://api.ucasal.edu.ar/otp/validate?usuario={{usuario}}&token={{token}}"
        else:
            return f"mocked_value_for_{key}"
    
    @staticmethod
    def get_int(key):
        return 300
