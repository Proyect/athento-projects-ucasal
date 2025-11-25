"""
Métricas personalizadas para Prometheus - Proyecto UCASAL
"""
from prometheus_client import Counter, Histogram, Gauge

# ============================================================================
# MÉTRICAS DE ACTAS
# ============================================================================

actas_total = Counter(
    'ucasal_actas_total',
    'Total de actas creadas',
    ['estado']
)

actas_firmadas_total = Counter(
    'ucasal_actas_firmadas_total',
    'Total de actas firmadas',
    ['docente']
)

actas_tiempo_firma = Histogram(
    'ucasal_actas_tiempo_firma_seconds',
    'Tiempo desde creación hasta firma',
    buckets=[60, 300, 600, 1800, 3600, 7200]  # 1min, 5min, 10min, 30min, 1h, 2h
)

actas_otp_enviados = Counter(
    'ucasal_actas_otp_enviados_total',
    'Total de códigos OTP enviados'
)

actas_otp_validos = Counter(
    'ucasal_actas_otp_validos_total',
    'Total de OTPs validados correctamente'
)

actas_otp_invalidos = Counter(
    'ucasal_actas_otp_invalidos_total',
    'Total de OTPs inválidos'
)

actas_blockchain_registradas = Counter(
    'ucasal_actas_blockchain_registradas_total',
    'Total de actas registradas en blockchain'
)

actas_blockchain_fallos = Counter(
    'ucasal_actas_blockchain_fallos_total',
    'Total de fallos en blockchain'
)

actas_rechazadas_total = Counter(
    'ucasal_actas_rechazadas_total',
    'Total de actas rechazadas'
)

# ============================================================================
# MÉTRICAS DE TÍTULOS
# ============================================================================

titulos_total = Counter(
    'ucasal_titulos_total',
    'Total de títulos recibidos',
    ['estado']
)

titulos_emitidos_total = Counter(
    'ucasal_titulos_emitidos_total',
    'Total de títulos emitidos'
)

titulos_tiempo_emision = Histogram(
    'ucasal_titulos_tiempo_emision_seconds',
    'Tiempo desde recepción hasta emisión',
    buckets=[86400, 172800, 604800, 2592000]  # 1d, 2d, 7d, 30d
)

titulos_cambios_estado = Counter(
    'ucasal_titulos_cambios_estado_total',
    'Total de cambios de estado',
    ['estado_anterior', 'estado_nuevo']
)

titulos_sla_expired = Counter(
    'ucasal_titulos_sla_expired_total',
    'Total de títulos con SLA expirado'
)

titulos_notificaciones_enviadas = Counter(
    'ucasal_titulos_notificaciones_enviadas_total',
    'Total de notificaciones enviadas',
    ['tipo']
)

# ============================================================================
# MÉTRICAS DE SERVICIOS EXTERNOS
# ============================================================================

ucasal_service_requests = Counter(
    'ucasal_service_requests_total',
    'Requests a servicios UCASAL',
    ['service', 'status']
)

ucasal_service_duration = Histogram(
    'ucasal_service_duration_seconds',
    'Tiempo de respuesta de servicios UCASAL',
    ['service'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ucasal_service_errors = Counter(
    'ucasal_service_errors_total',
    'Errores en servicios UCASAL',
    ['service', 'error_type']
)

athento_api_requests = Counter(
    'athento_api_requests_total',
    'Requests a API de Athento',
    ['endpoint', 'status']
)

athento_api_duration = Histogram(
    'athento_api_duration_seconds',
    'Tiempo de respuesta de Athento',
    ['endpoint'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

athento_api_errors = Counter(
    'athento_api_errors_total',
    'Errores en API de Athento',
    ['endpoint', 'error_type']
)

# ============================================================================
# MÉTRICAS DE AUTENTICACIÓN
# ============================================================================

auth_logins = Counter(
    'ucasal_auth_logins_total',
    'Total de logins',
    ['status']  # success, failure
)

auth_tokens_issued = Counter(
    'ucasal_auth_tokens_issued_total',
    'Total de tokens JWT emitidos'
)

auth_tokens_refreshed = Counter(
    'ucasal_auth_tokens_refreshed_total',
    'Total de tokens JWT refrescados'
)

auth_login_failures = Counter(
    'ucasal_auth_login_failures_total',
    'Total de logins fallidos'
)

# ============================================================================
# MÉTRICAS DE ERRORES
# ============================================================================

errors_total = Counter(
    'ucasal_errors_total',
    'Total de errores',
    ['error_type', 'endpoint']
)

exceptions_total = Counter(
    'ucasal_exceptions_total',
    'Total de excepciones',
    ['exception_type', 'endpoint']
)

validation_errors_total = Counter(
    'ucasal_validation_errors_total',
    'Total de errores de validación',
    ['field', 'endpoint']
)

# ============================================================================
# MÉTRICAS DE ENDPOINTS ESPECÍFICOS
# ============================================================================

endpoint_actas_sendotp_total = Counter(
    'ucasal_endpoint_actas_sendotp_total',
    'Total de requests a sendotp',
    ['status']
)

endpoint_actas_registerotp_total = Counter(
    'ucasal_endpoint_actas_registerotp_total',
    'Total de requests a registerotp',
    ['status']
)

endpoint_titulos_recibir_total = Counter(
    'ucasal_endpoint_titulos_recibir_total',
    'Total de requests a recibir título',
    ['status']
)

endpoint_titulos_estado_total = Counter(
    'ucasal_endpoint_titulos_estado_total',
    'Total de requests a cambio de estado',
    ['status']
)

endpoint_duration = Histogram(
    'ucasal_endpoint_duration_seconds',
    'Duración de endpoints',
    ['endpoint', 'method'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)



