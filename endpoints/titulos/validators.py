"""
Validadores personalizados para el sistema de títulos
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_dni_format(value):
    """Valida formato de DNI (7-8 dígitos)"""
    if not value:
        raise ValidationError(_('El DNI es requerido.'))
    
    dni_str = str(value)
    dni_pattern = r'^\d{7,8}$'
    if not re.match(dni_pattern, dni_str):
        raise ValidationError(_('El DNI debe tener entre 7 y 8 dígitos.'))
    
    return value


def validate_tipo_dni(value):
    """Valida tipo de DNI"""
    tipos_validos = ['DNI', 'LE', 'LC', 'DNI-LE-LC']
    if value not in tipos_validos:
        raise ValidationError(
            _(f'El tipo de DNI debe ser uno de: {", ".join(tipos_validos)}')
        )
    return value


def validate_filename_format(value):
    """Valida formato del filename: DNI/Lugar/FACULTAD/CARRERA/MODO/PLAN"""
    if not value:
        raise ValidationError(_('El filename es requerido.'))
    
    parts = value.split('/')
    if len(parts) != 6:
        raise ValidationError(
            _('El filename debe tener formato: DNI/Lugar/FACULTAD/CARRERA/MODO/PLAN')
        )
    
    # Validar que los componentes numéricos sean números
    # DNI (0), Lugar puede tener texto (1), SECTOR(2), CARRERA(3), MODO(4), PLAN(5)
    numeric_indices = [0, 2, 3, 4, 5]  # Índices que deben ser numéricos
    for i in range(len(parts)):
        if i in numeric_indices:
            if not parts[i].isdigit():
                raise ValidationError(
                    _(f'La parte {i+1} del filename debe ser numérica: {parts[i]}')
                )
    
    return value


def validate_facultad_codigo(value):
    """Valida código de facultad"""
    if not value:
        raise ValidationError(_('El código de facultad es requerido.'))
    
    # Código numérico
    if not str(value).isdigit():
        raise ValidationError(_('El código de facultad debe ser numérico.'))
    
    return value


def validate_titulo_estado_transicion(estado_actual, estado_nuevo):
    """
    Valida transiciones de estado válidas para títulos.
    
    NOTA: Las transiciones a blockchain están suspendidas temporalmente.
    El flujo ahora es: Firmado por SG → Título Emitido (sin blockchain)
    """
    from ucasal.utils import TituloStates
    
    # Transiciones válidas SIN blockchain (suspendido temporalmente)
    transiciones_validas = {
        TituloStates.recibido: [
            TituloStates.pendiente_aprobacion_ua,
            TituloStates.rechazado
        ],
        TituloStates.pendiente_aprobacion_ua: [
            TituloStates.aprobado_ua,
            TituloStates.rechazado
        ],
        TituloStates.aprobado_ua: [TituloStates.pendiente_aprobacion_r],
        TituloStates.pendiente_aprobacion_r: [
            TituloStates.aprobado_r,
            TituloStates.rechazado
        ],
        TituloStates.aprobado_r: [
            TituloStates.pendiente_firma_sg,
            # TituloStates.pendiente_blockchain  # SUSPENDIDO: blockchain deshabilitado
        ],
        TituloStates.pendiente_firma_sg: [TituloStates.firmado_sg],
        TituloStates.firmado_sg: [
            # TituloStates.pendiente_blockchain,  # SUSPENDIDO: blockchain deshabilitado
            TituloStates.titulo_emitido  # Flujo directo: Firmado por SG → Título Emitido
        ],
        # Estados de blockchain suspendidos - no se pueden usar en transiciones
        # TituloStates.pendiente_blockchain: [
        #     TituloStates.registrado_blockchain,
        #     TituloStates.fallo_blockchain
        # ],
        # TituloStates.registrado_blockchain: [TituloStates.titulo_emitido],
    }
    
    if estado_actual not in transiciones_validas:
        raise ValidationError(_(f'Estado actual "{estado_actual}" no válido.'))
    
    if estado_nuevo not in transiciones_validas[estado_actual]:
        raise ValidationError(
            _(f'No se puede cambiar de "{estado_actual}" a "{estado_nuevo}". '
              f'Transiciones válidas: {", ".join(transiciones_validas[estado_actual])}')
        )
    
    return estado_nuevo


def validate_plan_estudios(value):
    """Valida formato de plan de estudios"""
    if not value:
        raise ValidationError(_('El plan de estudios es requerido.'))
    
    # Plan debe ser numérico
    if not str(value).isdigit():
        raise ValidationError(_('El plan de estudios debe ser numérico.'))
    
    return value

