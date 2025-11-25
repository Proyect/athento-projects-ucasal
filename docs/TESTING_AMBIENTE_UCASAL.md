# Guía de Testing con Ambiente UCASAL

Esta guía explica cómo configurar y ejecutar pruebas del sistema contra el ambiente real de UCASAL (UAT o Producción), conectándose a los servicios externos reales en lugar de usar mocks locales.

## Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Configuración Inicial](#configuración-inicial)
3. [Configuración Manual](#configuración-manual)
4. [Verificación de Conectividad](#verificación-de-conectividad)
5. [Ejecución de Pruebas](#ejecución-de-pruebas)
6. [Troubleshooting](#troubleshooting)
7. [Checklist de Verificación](#checklist-de-verificación)

---

## Requisitos Previos

Antes de comenzar, asegúrate de tener:

- ✅ Acceso a las credenciales de los servicios UCASAL
- ✅ Acceso a la API de UCASAL (UAT o Producción)
- ✅ Python 3.8+ instalado
- ✅ Dependencias del proyecto instaladas (`pip install -r requirements.txt`)
- ✅ Archivo `.env` configurado (o usar el script de configuración)

---

## Configuración Inicial

### Opción 1: Configuración Interactiva (Recomendado)

El método más fácil es usar el script de configuración interactivo:

```bash
python scripts/configurar_ambiente_ucasal.py
```

Este script te guiará paso a paso:

1. **Seleccionar ambiente**: Local, UAT o Producción
2. **Ingresar credenciales**: Usuario y contraseña para servicios UCASAL
3. **Configurar API**: Credenciales de administrador de la API
4. **Validar conectividad**: Opcionalmente verificar la conexión

### Opción 2: Configuración Manual

Si prefieres configurar manualmente:

1. **Copiar archivo de ejemplo**:
   ```bash
   cp env.ucasal.sample .env
   ```

2. **Editar `.env`** con tus credenciales reales:
   ```bash
   # Editar con tu editor preferido
   nano .env
   # o
   notepad .env
   ```

3. **Completar las siguientes variables**:
   - `UCASAL_TOKEN_SVC_USER`: Usuario para servicio de token
   - `UCASAL_TOKEN_SVC_PASSWORD`: Contraseña para servicio de token
   - `API_ADMIN_USERNAME`: Usuario administrador de la API
   - `API_ADMIN_PASSWORD`: Contraseña del administrador

---

## Configuración Manual

### Variables de Entorno Requeridas

#### Servicios UCASAL

```bash
# Servicio de Token (Autenticación)
UCASAL_TOKEN_SVC_URL=https://ucasal-uat.athento.com/token
UCASAL_TOKEN_SVC_USER=<tu-usuario>
UCASAL_TOKEN_SVC_PASSWORD=<tu-password>

# Servicio de QR
UCASAL_QR_SVC_URL=https://ucasal-uat.athento.com/qr

# Servicio de Acortar URLs
UCASAL_SHORTEN_URL_SVC_URL=https://ucasal-uat.athento.com/shorten
UCASAL_SHORTEN_URL_SVC_ENV=desarrollo  # o 'produccion' para producción
```

#### Configuración de API

```bash
# URL base de la API
API_BASE_URL=https://ucasal-uat.athento.com

# Credenciales de administrador
API_ADMIN_USERNAME=<usuario-admin>
API_ADMIN_PASSWORD=<password-admin>
```

#### URLs de Validación

```bash
# URL de validación de actas
UCASAL_ACTA_VALIDATION_URL_TEMPLATE=https://ucasal-uat.athento.com/validar/{{uuid}}

# URL de validación de OTP
UCASAL_OTP_VALIDATION_URL_TEMPLATE=https://ucasal-uat.athento.com/otp/validate?usuario={{usuario}}&token={{token}}

# URL de validación de títulos
UCASAL_TITULO_VALIDATION_URL_TEMPLATE=https://www.ucasal.edu.ar/validar/index.php?d=titulo&e=testing&uuid={{uuid}}
```

### Diferencias entre Ambientes

#### Ambiente UAT (Testing)
- URLs: `https://ucasal-uat.athento.com/*`
- `UCASAL_SHORTEN_URL_SVC_ENV=desarrollo`
- URLs de validación incluyen parámetro `e=testing`

#### Ambiente Producción
- URLs: `https://api.ucasal.edu.ar/*`
- `UCASAL_SHORTEN_URL_SVC_ENV=produccion`
- URLs de validación sin parámetros de testing

---

## Verificación de Conectividad

Antes de ejecutar las pruebas completas, verifica que la conectividad con los servicios UCASAL esté funcionando:

```bash
python scripts/verificar_conectividad_ucasal.py
```

Este script verifica:

1. ✅ **Variables de entorno**: Todas las variables necesarias están configuradas
2. ✅ **Configuración cargada**: Los valores se leen correctamente
3. ✅ **Conectividad URLs**: Las URLs de los servicios son accesibles
4. ✅ **Autenticación**: Las credenciales son válidas y se puede obtener token
5. ✅ **Generación de QR**: El servicio de QR funciona correctamente
6. ✅ **Acortar URLs**: El servicio de acortar URLs funciona

### Salida Esperada

```
🔍 VERIFICACIÓN DE CONECTIVIDAD UCASAL
======================================================================

VERIFICACIÓN DE VARIABLES DE ENTORNO
======================================================================
  ✓ UCASAL_TOKEN_SVC_URL................................ OK
     Configurado: https://ucasal-uat.athento.com/token...
  ✓ UCASAL_TOKEN_SVC_USER................................ OK
     ...

VERIFICACIÓN DE AUTENTICACIÓN
======================================================================
  🔄 Intentando autenticación con usuario: usuario_test...
  ✓ Token Service Auth................................... OK
     Token obtenido: eyJ0eXAiOiJKV1QiLCJhbGc...

RESUMEN
======================================================================
  Pruebas exitosas: 6/6
  ✓ Variables
  ✓ Configuración
  ✓ Conectividad
  ✓ Autenticación
  ✓ Qr
  ✓ Acortar Url

✅ Todas las verificaciones pasaron exitosamente
```

Si alguna verificación falla, revisa la sección [Troubleshooting](#troubleshooting).

---

## Ejecución de Pruebas

Una vez verificada la conectividad, puedes ejecutar los scripts de prueba:

### 1. Pruebas Básicas

Prueba endpoints que no requieren datos previos:

```bash
python test_api_simple.py
```

Este script prueba:
- Información de API (`GET /`)
- Documentación (`GET /docs/`)
- Autenticación JWT (`POST /api/auth/login/`)
- Generación de QR (`POST /actas/qr/`)
- Obtener configuración (`POST /actas/getconfig/`)

### 2. Pruebas Avanzadas de Actas

Prueba endpoints de actas que requieren datos previos:

```bash
python test_api_avanzado.py
```

Este script prueba:
- Enviar OTP (`POST /actas/{uuid}/sendotp/`)
- Registrar OTP (`POST /actas/{uuid}/registerotp/`)
- Callback blockchain (`POST /actas/{uuid}/bfaresponse/`)
- Rechazar acta (`POST /actas/{uuid}/reject/`)

**Nota**: Requiere actas creadas previamente. Puedes crearlas usando:
```bash
python crear_actas_prueba.py
```

### 3. Pruebas de Títulos

Prueba endpoints de títulos:

```bash
python test_titulos_api.py
```

Este script prueba:
- Generar QR título (`POST /titulos/qr/`)
- Informar estado (`POST /titulos/{uuid}/estado/`)
- Validar OTP (`POST /titulos/{uuid}/validar-otp/`)
- Callback blockchain (`POST /titulos/{uuid}/bfaresponse/`)

**Nota**: Requiere títulos creados previamente. Puedes crearlos usando:
```bash
python crear_titulos_prueba.py
```

### Características de los Scripts

Los scripts de prueba han sido actualizados para soportar ambientes remotos:

- ✅ **Detección automática**: Detectan si es ambiente local o remoto
- ✅ **Timeouts ajustados**: Timeouts más largos para requests remotos (30s vs 5s)
- ✅ **Manejo de errores**: Mejor manejo de timeouts y errores de conexión
- ✅ **Mensajes informativos**: Mensajes claros sobre el estado de las pruebas

---

## Troubleshooting

### Error: "Timeout al conectar"

**Causa**: El servidor no responde o la red es lenta.

**Solución**:
1. Verifica que la URL en `API_BASE_URL` sea correcta
2. Verifica tu conectividad de red
3. Si es ambiente remoto, verifica que tengas acceso a la red/VPN necesaria
4. Aumenta el timeout en el script si es necesario

### Error: "No se pudo conectar"

**Causa**: El servidor no está disponible o la URL es incorrecta.

**Solución**:
1. Verifica que el servidor esté corriendo (si es local)
2. Verifica que la URL sea correcta
3. Verifica firewall/proxy si es ambiente remoto

### Error: "Token Service Auth - FAIL"

**Causa**: Credenciales incorrectas o servicio no disponible.

**Solución**:
1. Verifica `UCASAL_TOKEN_SVC_USER` y `UCASAL_TOKEN_SVC_PASSWORD`
2. Verifica que el servicio de token esté disponible
3. Ejecuta `verificar_conectividad_ucasal.py` para más detalles

### Error: "Variables de entorno no configuradas"

**Causa**: Faltan variables en el archivo `.env`.

**Solución**:
1. Verifica que el archivo `.env` exista
2. Ejecuta `configurar_ambiente_ucasal.py` para configurar
3. Revisa `env.ucasal.sample` para ver todas las variables necesarias

### Error: "Error de conexión al generar QR"

**Causa**: El servicio de QR no está disponible o hay problemas de red.

**Solución**:
1. Verifica `UCASAL_QR_SVC_URL`
2. Verifica conectividad con el servicio
3. Verifica que tengas token válido (ejecuta verificación de conectividad)

### Variables de Entorno No Se Cargan

**Causa**: El archivo `.env` no está en el directorio correcto o no se carga.

**Solución**:
1. Asegúrate de que `.env` esté en el directorio raíz del proyecto
2. Verifica que `python-dotenv` esté instalado: `pip install python-dotenv`
3. Reinicia el script después de modificar `.env`

---

## Checklist de Verificación

Antes de ejecutar pruebas en ambiente UCASAL, verifica:

### Configuración
- [ ] Archivo `.env` creado y configurado
- [ ] Todas las variables de entorno requeridas están presentes
- [ ] Credenciales de servicios UCASAL son correctas
- [ ] Credenciales de API son correctas
- [ ] URLs apuntan al ambiente correcto (UAT/Producción)

### Conectividad
- [ ] Script de verificación de conectividad pasa todas las pruebas
- [ ] Puedes obtener token de autenticación
- [ ] Servicios de QR y acortar URLs funcionan
- [ ] API está accesible desde tu ubicación

### Datos de Prueba
- [ ] Actas de prueba creadas (si vas a probar endpoints de actas)
- [ ] Títulos de prueba creados (si vas a probar endpoints de títulos)
- [ ] UUIDs de prueba disponibles

### Scripts
- [ ] Scripts de prueba actualizados y funcionando
- [ ] Timeouts configurados apropiadamente
- [ ] Manejo de errores funciona correctamente

---

## Próximos Pasos

Después de configurar el ambiente y verificar la conectividad:

1. **Ejecuta pruebas básicas**: `python test_api_simple.py`
2. **Crea datos de prueba**: `python crear_actas_prueba.py` o `python crear_titulos_prueba.py`
3. **Ejecuta pruebas avanzadas**: `python test_api_avanzado.py` o `python test_titulos_api.py`
4. **Revisa resultados**: Analiza los resultados y corrige cualquier problema
5. **Documenta problemas**: Si encuentras problemas, documenta para el equipo

---

## Referencias

- **Guía de Pruebas del Sistema**: `docs/GUIA_PRUEBAS_SISTEMA.md`
- **Documentación de Endpoints**: `docs/ENDPOINTS_SISTEMA.md`
- **Configuración de Ejemplo**: `env.ucasal.sample`
- **Script de Configuración**: `scripts/configurar_ambiente_ucasal.py`
- **Script de Verificación**: `scripts/verificar_conectividad_ucasal.py`

---

## Notas Importantes

⚠️ **Seguridad**:
- Nunca commitees el archivo `.env` con credenciales reales
- Usa variables de entorno o un gestor de secretos en producción
- Rota credenciales regularmente

⚠️ **Ambiente de Producción**:
- Ten cuidado al probar en producción
- Usa datos de prueba, no datos reales
- Verifica que los endpoints de producción estén disponibles

⚠️ **Rate Limiting**:
- Algunos servicios pueden tener límites de rate
- Si ves errores 429, espera antes de reintentar
- Considera usar ambiente UAT para pruebas extensivas

---

**Última actualización**: 2025-01-31

