# Monitoreo con Prometheus y Grafana - Proyecto UCASAL

## 📊 Introducción a Prometheus y Grafana

### ¿Qué es Prometheus?

**Prometheus** es un sistema de monitoreo y alertas de código abierto, diseñado para sistemas distribuidos y microservicios. Fue desarrollado originalmente por SoundCloud y ahora es parte de la Cloud Native Computing Foundation (CNCF).

#### Características Principales:
- **Recolección de métricas**: Recolecta métricas de aplicaciones mediante HTTP endpoints
- **Almacenamiento de series temporales**: Almacena datos en formato de series temporales
- **Lenguaje de consulta (PromQL)**: Permite consultas potentes y agregaciones
- **Alertas**: Sistema integrado de alertas basado en reglas
- **Modelo pull**: Las aplicaciones exponen métricas y Prometheus las "jala"
- **Multi-dimensional**: Métricas identificadas por nombre y pares clave-valor (labels)

### ¿Qué es Grafana?

**Grafana** es una plataforma de visualización y análisis de código abierto, especializada en la visualización de métricas de series temporales.

#### Características Principales:
- **Dashboards interactivos**: Creación de dashboards personalizados
- **Múltiples fuentes de datos**: Soporta Prometheus, InfluxDB, Elasticsearch, etc.
- **Alertas visuales**: Sistema de alertas integrado
- **Anotaciones**: Marcadores temporales en gráficos
- **Exportación/Importación**: Compartir dashboards fácilmente

### ¿Cómo Funcionan Juntos?

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Aplicación │         │  Prometheus  │         │   Grafana   │
│   Django    │◄────────│   (Pull)     │◄────────│ (Visualiza) │
│             │         │              │         │             │
│  /metrics   │         │  Almacena    │         │  Dashboards │
└─────────────┘         └──────────────┘         └─────────────┘
     │                        │                        │
     │                        │                        │
     └────────────────────────┴────────────────────────┘
                    Alertas (Alertmanager)
```

1. **Aplicación Django** expone métricas en endpoint `/metrics`
2. **Prometheus** hace scraping periódico (pull) de estas métricas
3. **Prometheus** almacena las métricas como series temporales
4. **Grafana** consulta Prometheus y visualiza las métricas en dashboards
5. **Alertmanager** (opcional) envía alertas basadas en reglas

---

## 🎯 ¿Por Qué Prometheus y Grafana para UCASAL?

### Beneficios para el Proyecto

1. **Observabilidad Completa**
   - Ver el estado del sistema en tiempo real
   - Identificar problemas antes de que afecten a usuarios
   - Entender patrones de uso y comportamiento

2. **Métricas de Negocio**
   - Cantidad de actas firmadas por día
   - Tiempo promedio de procesamiento de títulos
   - Tasa de éxito de operaciones OTP
   - Errores en integraciones con servicios externos

3. **Métricas Técnicas**
   - Performance de endpoints (latencia, throughput)
   - Uso de recursos (CPU, memoria, base de datos)
   - Errores y excepciones
   - Tiempo de respuesta de servicios externos

4. **Alertas Proactivas**
   - Notificar cuando un servicio externo falla
   - Alertar sobre alta tasa de errores
   - Detectar degradación de performance

---

## 📈 Métricas Específicas para UCASAL

### 1. Métricas de Actas

#### Métricas de Negocio
- `ucasal_actas_total`: Total de actas creadas
- `ucasal_actas_por_estado`: Actas agrupadas por estado (recibida, pendiente_otp, firmada, etc.)
- `ucasal_actas_firmadas_total`: Total de actas firmadas exitosamente
- `ucasal_actas_rechazadas_total`: Total de actas rechazadas
- `ucasal_actas_por_docente`: Actas agrupadas por docente

#### Métricas de Proceso
- `ucasal_actas_otp_enviados_total`: Total de códigos OTP enviados
- `ucasal_actas_otp_validos_total`: Total de OTPs validados correctamente
- `ucasal_actas_otp_invalidos_total`: Total de OTPs inválidos
- `ucasal_actas_blockchain_registradas_total`: Total de actas registradas en blockchain
- `ucasal_actas_blockchain_fallos_total`: Total de fallos en blockchain

#### Métricas de Performance
- `ucasal_actas_tiempo_firma_seconds`: Tiempo desde creación hasta firma (histograma)
- `ucasal_actas_tiempo_procesamiento_seconds`: Tiempo total de procesamiento
- `ucasal_actas_endpoint_duration_seconds`: Latencia de endpoints de actas

### 2. Métricas de Títulos

#### Métricas de Negocio
- `ucasal_titulos_total`: Total de títulos recibidos
- `ucasal_titulos_por_estado`: Títulos agrupados por estado
- `ucasal_titulos_emitidos_total`: Total de títulos emitidos
- `ucasal_titulos_rechazados_total`: Total de títulos rechazados
- `ucasal_titulos_por_carrera`: Títulos agrupados por carrera

#### Métricas de Proceso
- `ucasal_titulos_cambios_estado_total`: Total de cambios de estado
- `ucasal_titulos_notificaciones_enviadas_total`: Total de notificaciones enviadas
- `ucasal_titulos_sla_expired_total`: Total de títulos con SLA expirado

#### Métricas de Performance
- `ucasal_titulos_tiempo_aprobacion_seconds`: Tiempo de aprobación
- `ucasal_titulos_tiempo_emision_seconds`: Tiempo desde recepción hasta emisión
- `ucasal_titulos_endpoint_duration_seconds`: Latencia de endpoints de títulos

### 3. Métricas de API

#### Métricas Generales
- `http_requests_total`: Total de requests HTTP (por método, endpoint, status)
- `http_request_duration_seconds`: Duración de requests (histograma)
- `http_request_size_bytes`: Tamaño de requests
- `http_response_size_bytes`: Tamaño de responses

#### Métricas por Endpoint
- `ucasal_endpoint_actas_sendotp_total`: Requests a sendotp
- `ucasal_endpoint_actas_registerotp_total`: Requests a registerotp
- `ucasal_endpoint_titulos_recibir_total`: Requests a recibir título
- `ucasal_endpoint_titulos_estado_total`: Requests a cambio de estado

### 4. Métricas de Servicios Externos

#### Integración UCASAL
- `ucasal_service_requests_total`: Requests a servicios UCASAL (por servicio)
- `ucasal_service_duration_seconds`: Tiempo de respuesta de servicios UCASAL
- `ucasal_service_errors_total`: Errores en servicios UCASAL
- `ucasal_service_otp_validations_total`: Validaciones OTP realizadas
- `ucasal_service_blockchain_registrations_total`: Registros en blockchain

#### Integración Athento
- `athento_api_requests_total`: Requests a API de Athento
- `athento_api_duration_seconds`: Tiempo de respuesta de Athento
- `athento_api_errors_total`: Errores en Athento

### 5. Métricas de Sistema

#### Base de Datos
- `django_db_queries_total`: Total de queries a la base de datos
- `django_db_query_duration_seconds`: Duración de queries
- `django_db_connections_active`: Conexiones activas a la BD

#### Cache
- `django_cache_hits_total`: Cache hits
- `django_cache_misses_total`: Cache misses
- `django_cache_operations_total`: Operaciones de cache

#### Autenticación
- `ucasal_auth_logins_total`: Total de logins
- `ucasal_auth_login_failures_total`: Logins fallidos
- `ucasal_auth_tokens_issued_total`: Tokens JWT emitidos
- `ucasal_auth_tokens_refreshed_total`: Tokens refrescados

### 6. Métricas de Errores

- `ucasal_errors_total`: Total de errores (por tipo)
- `ucasal_exceptions_total`: Total de excepciones (por tipo)
- `ucasal_validation_errors_total`: Errores de validación
- `ucasal_integration_errors_total`: Errores de integración

---

## 🔧 Implementación en el Proyecto UCASAL

### Paso 1: Instalar Dependencias

```bash
# Agregar a requirements.txt
django-prometheus>=2.3.1
prometheus-client>=0.19.0
```

### Paso 2: Configurar Django Prometheus

#### settings.py

```python
INSTALLED_APPS = [
    # ... otras apps
    'django_prometheus',
    # ... resto de apps
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # Al inicio
    # ... otros middlewares
    'django_prometheus.middleware.PrometheusAfterMiddleware',   # Al final
]

# URLs de Prometheus
PROMETHEUS_EXPORT_MIGRATIONS = False
```

#### urls.py

```python
from django.urls import path, include

urlpatterns = [
    # ... otras URLs
    path('', include('django_prometheus.urls')),
]
```

### Paso 3: Crear Métricas Personalizadas

#### core/metrics.py

```python
from prometheus_client import Counter, Histogram, Gauge
from django_prometheus.middleware import PrometheusAfterMiddleware

# Métricas de Actas
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

# Métricas de Títulos
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

# Métricas de Servicios Externos
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

# Métricas de Errores
errors_total = Counter(
    'ucasal_errors_total',
    'Total de errores',
    ['error_type', 'endpoint']
)

# Métricas de Autenticación
auth_logins = Counter(
    'ucasal_auth_logins_total',
    'Total de logins',
    ['status']  # success, failure
)

auth_tokens_issued = Counter(
    'ucasal_auth_tokens_issued_total',
    'Total de tokens JWT emitidos'
)
```

### Paso 4: Instrumentar Código

#### endpoints/actas/actas.py

```python
from core.metrics import (
    actas_total, actas_firmadas_total, actas_tiempo_firma,
    actas_otp_enviados, actas_otp_validos, actas_otp_invalidos,
    actas_blockchain_registradas, actas_blockchain_fallos,
    ucasal_service_requests, ucasal_service_duration,
    ucasal_service_errors
)
from prometheus_client import Summary
import time

# Decorador para medir tiempo de endpoints
def track_endpoint_metric(metric_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                ucasal_service_duration.labels(service=metric_name).observe(duration)
                ucasal_service_requests.labels(service=metric_name, status=status).inc()
        return wrapper
    return decorator

@default_permissions
@traceback_ret
def sendotp(request, uuid):
    """Enviar código OTP"""
    # ... código existente ...
    
    # Incrementar métrica
    actas_otp_enviados.inc()
    
    # ... resto del código ...

@default_permissions
@traceback_ret
def registerotp(request, uuid):
    """Registrar OTP y firmar"""
    start_time = time.time()
    
    try:
        # Validar OTP
        if not UcasalServices.validate_otp(...):
            actas_otp_invalidos.inc()
            raise InvalidOtpError(...)
        
        actas_otp_validos.inc()
        
        # ... proceso de firma ...
        
        # Registrar en blockchain
        try:
            UcasalServices.register_in_blockchain(...)
            actas_blockchain_registradas.inc()
        except Exception as e:
            actas_blockchain_fallos.inc()
            raise
        
        # Calcular tiempo de firma
        acta = Acta.objects.get(uuid=uuid)
        if acta.fecha_creacion and acta.fecha_firma:
            tiempo_firma = (acta.fecha_firma - acta.fecha_creacion).total_seconds()
            actas_tiempo_firma.observe(tiempo_firma)
        
        actas_firmadas_total.labels(docente=acta.docente_asignado).inc()
        
    except Exception as e:
        # ... manejo de errores ...
```

#### external_services/ucasal/ucasal_services.py

```python
from core.metrics import (
    ucasal_service_requests, ucasal_service_duration,
    ucasal_service_errors
)
import time

class UcasalServices:
    @classmethod
    def validate_otp(cls, user: str, otp: int):
        start_time = time.time()
        service_name = 'validate_otp'
        
        try:
            # ... código existente ...
            
            duration = time.time() - start_time
            ucasal_service_duration.labels(service=service_name).observe(duration)
            ucasal_service_requests.labels(service=service_name, status='success').inc()
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            ucasal_service_duration.labels(service=service_name).observe(duration)
            ucasal_service_requests.labels(service=service_name, status='error').inc()
            ucasal_service_errors.labels(service=service_name, error_type=type(e).__name__).inc()
            raise
```

### Paso 5: Configurar Prometheus

#### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ucasal-django'
    static_configs:
      - targets: ['django:8012']
        labels:
          service: 'ucasal-api'
          environment: 'production'
    
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']
    
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Paso 6: Configurar Docker Compose

#### docker-compose.yml

```yaml
version: '3.8'

services:
  # ... servicios existentes ...
  
  prometheus:
    image: prom/prometheus:latest
    container_name: ucasal-prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    networks:
      - ucasal-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: ucasal-grafana
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    networks:
      - ucasal-network
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:

networks:
  ucasal-network:
    driver: bridge
```

### Paso 7: Crear Dashboards en Grafana

#### Ejemplo de Dashboard JSON

```json
{
  "dashboard": {
    "title": "UCASAL - Sistema de Actas y Títulos",
    "panels": [
      {
        "title": "Actas por Estado",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(ucasal_actas_total) by (estado)",
            "legendFormat": "{{estado}}"
          }
        ]
      },
      {
        "title": "Tiempo Promedio de Firma",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, ucasal_actas_tiempo_firma_seconds_bucket)",
            "legendFormat": "P95"
          }
        ]
      },
      {
        "title": "Tasa de Éxito de OTP",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(ucasal_actas_otp_validos_total[5m]) / rate(ucasal_actas_otp_enviados_total[5m]) * 100"
          }
        ]
      }
    ]
  }
}
```

---

## 📊 Dashboards Recomendados

### Dashboard 1: Visión General del Sistema

**Panel 1**: Requests por segundo
- `rate(http_requests_total[1m])`

**Panel 2**: Latencia promedio
- `rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])`

**Panel 3**: Tasa de errores
- `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])`

**Panel 4**: Actas por estado (pie chart)
- `sum(ucasal_actas_total) by (estado)`

**Panel 5**: Títulos por estado (pie chart)
- `sum(ucasal_titulos_total) by (estado)`

### Dashboard 2: Métricas de Actas

**Panel 1**: Actas creadas hoy
- `increase(ucasal_actas_total[24h])`

**Panel 2**: Actas firmadas vs rechazadas
- `rate(ucasal_actas_firmadas_total[1h])`
- `rate(ucasal_actas_rechazadas_total[1h])`

**Panel 3**: Tiempo de procesamiento (P50, P95, P99)
- `histogram_quantile(0.50, ucasal_actas_tiempo_firma_seconds_bucket)`
- `histogram_quantile(0.95, ucasal_actas_tiempo_firma_seconds_bucket)`
- `histogram_quantile(0.99, ucasal_actas_tiempo_firma_seconds_bucket)`

**Panel 4**: Tasa de éxito de OTP
- `rate(ucasal_actas_otp_validos_total[5m]) / rate(ucasal_actas_otp_enviados_total[5m])`

**Panel 5**: Registros en blockchain
- `rate(ucasal_actas_blockchain_registradas_total[1h])`
- `rate(ucasal_actas_blockchain_fallos_total[1h])`

### Dashboard 3: Métricas de Títulos

**Panel 1**: Títulos recibidos hoy
- `increase(ucasal_titulos_total[24h])`

**Panel 2**: Tiempo promedio de emisión
- `histogram_quantile(0.50, ucasal_titulos_tiempo_emision_seconds_bucket)`

**Panel 3**: Cambios de estado
- `rate(ucasal_titulos_cambios_estado_total[1h])`

**Panel 4**: Títulos con SLA expirado
- `ucasal_titulos_sla_expired_total`

### Dashboard 4: Servicios Externos

**Panel 1**: Latencia de servicios UCASAL
- `histogram_quantile(0.95, ucasal_service_duration_seconds_bucket{service="validate_otp"})`
- `histogram_quantile(0.95, ucasal_service_duration_seconds_bucket{service="register_in_blockchain"})`

**Panel 2**: Tasa de errores por servicio
- `rate(ucasal_service_errors_total[5m]) by (service)`

**Panel 3**: Requests por servicio
- `rate(ucasal_service_requests_total[1m]) by (service)`

### Dashboard 5: Performance y Recursos

**Panel 1**: CPU y Memoria
- Métricas del sistema (requiere node-exporter)

**Panel 2**: Queries de base de datos
- `rate(django_db_queries_total[1m])`
- `rate(django_db_query_duration_seconds_sum[1m])`

**Panel 3**: Cache hit rate
- `rate(django_cache_hits_total[1m]) / (rate(django_cache_hits_total[1m]) + rate(django_cache_misses_total[1m]))`

---

## 🚨 Alertas Recomendadas

### Alertas Críticas

#### 1. Alta Tasa de Errores
```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
  for: 5m
  annotations:
    summary: "Alta tasa de errores HTTP"
    description: "Tasa de errores 5xx > 10% en los últimos 5 minutos"
```

#### 2. Servicio Externo Caído
```yaml
- alert: ExternalServiceDown
  expr: rate(ucasal_service_errors_total[5m]) > 0.05
  for: 5m
  annotations:
    summary: "Servicio externo con alta tasa de errores"
    description: "{{ $labels.service }} tiene > 5% de errores"
```

#### 3. Latencia Alta
```yaml
- alert: HighLatency
  expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 5
  for: 10m
  annotations:
    summary: "Latencia P95 > 5 segundos"
```

#### 4. Tasa de Fallos en Blockchain
```yaml
- alert: BlockchainFailures
  expr: rate(ucasal_actas_blockchain_fallos_total[10m]) > 0.1
  for: 5m
  annotations:
    summary: "Alta tasa de fallos en blockchain"
    description: "> 10% de fallos en registro blockchain"
```

### Alertas de Negocio

#### 5. Tasa de OTP Inválidos
```yaml
- alert: HighInvalidOTPRate
  expr: rate(ucasal_actas_otp_invalidos_total[10m]) / rate(ucasal_actas_otp_enviados_total[10m]) > 0.2
  for: 10m
  annotations:
    summary: "Alta tasa de OTPs inválidos"
    description: "> 20% de OTPs inválidos"
```

#### 6. SLA de Títulos Expirado
```yaml
- alert: TitulosSLAExpired
  expr: increase(ucasal_titulos_sla_expired_total[1h]) > 5
  for: 0m
  annotations:
    summary: "Títulos con SLA expirado"
    description: "{{ $value }} títulos con SLA expirado en la última hora"
```

---

## 🔍 Consultas PromQL Útiles

### Consultas Básicas

```promql
# Total de actas firmadas hoy
increase(ucasal_actas_firmadas_total[24h])

# Tasa de requests por segundo
rate(http_requests_total[1m])

# Latencia promedio
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Percentil 95 de latencia
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# Tasa de errores
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

### Consultas Avanzadas

```promql
# Actas por estado (últimas 24 horas)
sum(increase(ucasal_actas_total[24h])) by (estado)

# Tiempo promedio de firma por docente
avg(ucasal_actas_tiempo_firma_seconds) by (docente)

# Tasa de éxito de OTP (últimos 5 minutos)
rate(ucasal_actas_otp_validos_total[5m]) / rate(ucasal_actas_otp_enviados_total[5m])

# Top 5 endpoints más lentos
topk(5, histogram_quantile(0.95, http_request_duration_seconds_bucket))
```

---

## 📝 Próximos Pasos

### Implementación Inmediata
1. ✅ Instalar `django-prometheus`
2. ✅ Configurar middleware de Prometheus
3. ✅ Crear métricas básicas
4. ✅ Instrumentar endpoints críticos

### Corto Plazo
1. ⏳ Configurar Prometheus en Docker
2. ⏳ Configurar Grafana
3. ⏳ Crear dashboards básicos
4. ⏳ Configurar alertas críticas

### Mediano Plazo
1. ⏳ Instrumentar todos los endpoints
2. ⏳ Agregar métricas de negocio
3. ⏳ Crear dashboards avanzados
4. ⏳ Configurar Alertmanager

### Largo Plazo
1. ⏳ Métricas de negocio avanzadas
2. ⏳ Análisis predictivo
3. ⏳ Integración con otros sistemas
4. ⏳ Machine learning para detección de anomalías

---

## 📚 Recursos Adicionales

- [Documentación de Prometheus](https://prometheus.io/docs/)
- [Documentación de Grafana](https://grafana.com/docs/)
- [Django Prometheus](https://github.com/korfuri/django-prometheus)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)

---

**Última actualización**: 2025-01-31  
**Versión**: 1.0.0



