"""
Excepciones personalizadas para el sistema UCASAL
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class AthentoseError(Exception):
    """Excepción base para errores del sistema Athento"""
    pass

class UCASALServiceError(AthentoseError):
    """Error en servicios externos de UCASAL"""
    pass

class ActaNotFoundError(AthentoseError):
    """Acta no encontrada"""
    pass

class InvalidActaStateError(AthentoseError):
    """Estado de acta inválido para la operación"""
    pass

class OTPValidationError(AthentoseError):
    """Error en validación de OTP"""
    pass

class BlockchainServiceError(AthentoseError):
    """Error en servicios de blockchain"""
    pass

class QRGenerationError(AthentoseError):
    """Error en generación de código QR"""
    pass

class PDFSigningError(AthentoseError):
    """Error en firma de PDF"""
    pass

class NotificationError(AthentoseError):
    """Error en envío de notificaciones"""
    pass

class ConfigurationError(AthentoseError):
    """Error de configuración"""
    pass

class ValidationError(ValidationError):
    """Error de validación personalizado"""
    def __init__(self, message, field=None, code=None):
        super().__init__(message, code)
        self.field = field

class BusinessLogicError(AthentoseError):
    """Error de lógica de negocio"""
    pass

class ExternalServiceTimeoutError(AthentoseError):
    """Timeout en servicio externo"""
    pass

class ExternalServiceUnavailableError(AthentoseError):
    """Servicio externo no disponible"""
    pass

class DataIntegrityError(AthentoseError):
    """Error de integridad de datos"""
    pass

class PermissionDeniedError(AthentoseError):
    """Permisos insuficientes"""
    pass

class RateLimitExceededError(AthentoseError):
    """Límite de velocidad excedido"""
    pass

class MaintenanceModeError(AthentoseError):
    """Sistema en modo mantenimiento"""
    pass

class InvalidOTPError(Exception):
    """Código OTP inválido o expirado"""
    pass