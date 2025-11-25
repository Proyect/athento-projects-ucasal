"""
Implementación real de SpAthentoConfig que lee variables de entorno del archivo .env
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class SpAthentoConfig:
    """
    Configuración que lee valores desde variables de entorno.
    Mapea las claves esperadas por UcasalConfig a variables de entorno.
    """
    
    # Mapeo de claves de configuración a variables de entorno
    _ENV_MAPPING = {
        'ucasal.endpoint.gettoken.url': 'UCASAL_TOKEN_SVC_URL',
        'ucasal.endpoint.gettoken.usuario': 'UCASAL_TOKEN_SVC_USER',
        'ucasal.endpoint.gettoken.clave': 'UCASAL_TOKEN_SVC_PASSWORD',
        'ucasal.endpoint.qr.url': 'UCASAL_QR_SVC_URL',
        'ucasal.endpoint.stamps.url': 'UCASAL_STAMPS_SVC_URL',
        'ucasal.endpoint.change_acta.url': 'UCASAL_CHANGE_ACTA_SVC_URL',
        'ucasal.endpoint.acortar_url.url': 'UCASAL_SHORTEN_URL_SVC_URL',
        'ucasal.endpoint.acortar_url.env': 'UCASAL_SHORTEN_URL_SVC_ENV',
        'ucasal.acta.validation_url_template': 'UCASAL_ACTA_VALIDATION_URL_TEMPLATE',
        'ucasal.endopint.otp.validation_url_template': 'UCASAL_OTP_VALIDATION_URL_TEMPLATE',
        'ucasal.titulo.validation_url_template': 'UCASAL_TITULO_VALIDATION_URL_TEMPLATE',
        'ucasal.otp_validity_seconds': 'UCASAL_OTP_VALIDITY_SECONDS',
    }
    
    # Valores por defecto si no se encuentra la variable de entorno
    _DEFAULTS = {
        'ucasal.endpoint.gettoken.url': 'https://api.ucasal.edu.ar/token',
        'ucasal.endpoint.qr.url': 'https://api.qrserver.com/v1/create-qr-code/',
        'ucasal.endpoint.stamps.url': 'https://api.ucasal.edu.ar/stamps',
        'ucasal.endpoint.change_acta.url': 'https://api.ucasal.edu.ar/change-acta',
        'ucasal.endpoint.acortar_url.url': 'https://api.ucasal.edu.ar/shorten',
        'ucasal.endpoint.acortar_url.env': 'desarrollo',
        'ucasal.acta.validation_url_template': 'https://ucasal.edu.ar/validar/{{uuid}}',
        'ucasal.endopint.otp.validation_url_template': 'https://api.ucasal.edu.ar/otp/validate?usuario={{usuario}}&token={{token}}',
        'ucasal.titulo.validation_url_template': 'https://www.ucasal.edu.ar/validar/index.php?d=titulo&uuid={{uuid}}',
        'ucasal.otp_validity_seconds': '300',
    }
    
    @staticmethod
    def get_str(key, is_secret=False, default=None):
        """
        Obtiene un valor de configuración como string desde variables de entorno.
        
        Args:
            key: Clave de configuración (ej: 'ucasal.endpoint.gettoken.url')
            is_secret: Si es True, el valor es sensible (no se loguea)
            default: Valor por defecto si no se encuentra
        
        Returns:
            str: Valor de la configuración
        """
        # Buscar en el mapeo
        env_var = SpAthentoConfig._ENV_MAPPING.get(key)
        
        if env_var:
            # Leer desde variable de entorno
            value = os.getenv(env_var)
            if value:
                return value
        
        # Si no se encontró, usar default proporcionado o el default del mapeo
        if default is not None:
            return default
        
        return SpAthentoConfig._DEFAULTS.get(key, '')
    
    @staticmethod
    def get_int(key, default=None):
        """
        Obtiene un valor de configuración como entero desde variables de entorno.
        
        Args:
            key: Clave de configuración
            default: Valor por defecto si no se encuentra
        
        Returns:
            int: Valor de la configuración como entero
        """
        str_value = SpAthentoConfig.get_str(key, default=str(default) if default is not None else '300')
        
        try:
            return int(str_value)
        except (ValueError, TypeError):
            # Si no se puede convertir, usar default o 300
            return default if default is not None else 300

