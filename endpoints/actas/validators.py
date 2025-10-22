"""
Validadores personalizados para el sistema de actas
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_otp_code(value):
    """Valida que el código OTP sea numérico y tenga 6 dígitos"""
    if not isinstance(value, (int, str)):
        raise ValidationError(_('El código OTP debe ser un número.'))
    
    # Convertir a string para validar
    otp_str = str(value)
    
    if not otp_str.isdigit():
        raise ValidationError(_('El código OTP solo puede contener dígitos.'))
    
    if len(otp_str) != 6:
        raise ValidationError(_('El código OTP debe tener exactamente 6 dígitos.'))
    
    return int(value)

def validate_ip_address(value):
    """Valida que la IP sea válida"""
    if not value:
        raise ValidationError(_('La dirección IP es requerida.'))
    
    # Patrón básico para IPv4
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    
    if not re.match(ipv4_pattern, value):
        raise ValidationError(_('Ingrese una dirección IP válida.'))
    
    return value

def validate_coordinates(latitude, longitude):
    """Valida coordenadas GPS"""
    if latitude is not None:
        if not isinstance(latitude, (int, float)):
            raise ValidationError(_('La latitud debe ser un número.'))
        
        if latitude < -90 or latitude > 90:
            raise ValidationError(_('La latitud debe estar entre -90 y 90 grados.'))
    
    if longitude is not None:
        if not isinstance(longitude, (int, float)):
            raise ValidationError(_('La longitud debe ser un número.'))
        
        if longitude < -180 or longitude > 180:
            raise ValidationError(_('La longitud debe estar entre -180 y 180 grados.'))
    
    return latitude, longitude

def validate_user_agent(value):
    """Valida el user agent"""
    if not value:
        raise ValidationError(_('El user agent es requerido.'))
    
    if len(value) < 10:
        raise ValidationError(_('El user agent parece ser muy corto.'))
    
    if len(value) > 500:
        raise ValidationError(_('El user agent es demasiado largo.'))
    
    return value

def validate_accuracy(value):
    """Valida la precisión GPS"""
    if not value:
        raise ValidationError(_('La precisión GPS es requerida.'))
    
    # Debe contener un número seguido de 'm' (metros)
    accuracy_pattern = r'^\d+(\.\d+)?m$'
    
    if not re.match(accuracy_pattern, value):
        raise ValidationError(_('La precisión debe estar en formato "Xm" (ej: "10m").'))
    
    return value

def validate_motivo_rechazo(value):
    """Valida el motivo de rechazo"""
    if not value:
        raise ValidationError(_('El motivo de rechazo es requerido.'))
    
    if len(value.strip()) < 10:
        raise ValidationError(_('El motivo de rechazo debe tener al menos 10 caracteres.'))
    
    if len(value) > 500:
        raise ValidationError(_('El motivo de rechazo es demasiado largo.'))
    
    return value.strip()

def validate_uuid_format(value):
    """Valida formato de UUID"""
    if not value:
        raise ValidationError(_('El UUID es requerido.'))
    
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    if not re.match(uuid_pattern, str(value), re.IGNORECASE):
        raise ValidationError(_('El UUID debe tener un formato válido.'))
    
    return value

def validate_estado_transicion(estado_actual, estado_nuevo):
    """Valida transiciones de estado válidas"""
    transiciones_validas = {
        'recibida': ['pendiente_otp', 'rechazada'],
        'pendiente_otp': ['firmada', 'rechazada'],
        'firmada': ['pendiente_blockchain'],
        'pendiente_blockchain': ['firmada', 'fallo_blockchain'],
        'fallo_blockchain': ['pendiente_otp'],
        'rechazada': ['pendiente_otp']  # Solo para reactivación
    }
    
    if estado_actual not in transiciones_validas:
        raise ValidationError(_(f'Estado actual "{estado_actual}" no válido.'))
    
    if estado_nuevo not in transiciones_validas[estado_actual]:
        raise ValidationError(
            _(f'No se puede cambiar de "{estado_actual}" a "{estado_nuevo}". '
              f'Transiciones válidas: {", ".join(transiciones_validas[estado_actual])}')
        )
    
    return estado_nuevo


