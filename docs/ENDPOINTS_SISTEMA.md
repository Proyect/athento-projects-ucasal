# 📋 ENDPOINTS DEL SISTEMA UCASAL

## 🌐 URL Base
```
http://localhost:8012
```

---

## 🔐 Endpoints de Autenticación

### 1. Login (Obtener Token JWT)
```
POST /api/auth/login/
```
**Body:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```
**Respuesta:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2. Refresh Token
```
POST /api/auth/refresh/
```
**Body:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
**Respuesta:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## 📄 Endpoints Generales

### 3. Información de la API
```
GET /
```
**Respuesta:**
```json
{
  "message": "UCASAL API - Sistema de Actas y Títulos",
  "version": "1.0.0",
  "endpoints": {
    "admin": "/admin/",
    "actas": "/actas/",
    "titulos": "/titulos/",
    "qr": "/actas/qr/",
    "getconfig": "/actas/getconfig/",
    "docs": "/docs/"
  }
}
```

### 4. Documentación
```
GET /docs/
```
**Respuesta:** JSON con documentación completa de todos los endpoints

### 5. Panel de Administración
```
GET /admin/
```
**Nota:** Requiere login de administrador

---

## 📝 Endpoints de ACTAS

### 6. Generar Código QR
```
POST /actas/qr/
```
**Headers:**
```
Content-Type: application/json
```
**Body:**
```json
{
  "url": "https://www.ucasal.edu.ar/validar/acta/test-uuid"
}
```
**Respuesta:** Imagen PNG del código QR

### 7. Obtener Configuración
```
POST /actas/getconfig/
```
**Headers:**
```
Content-Type: application/json
```
**Body:**
```json
{
  "key": "test_key",
  "is_secret": false
}
```
**Respuesta:** Valor de configuración (string)

### 8. Enviar Código OTP
```
POST /actas/{uuid}/sendotp/
```
**Parámetros URL:**
- `uuid`: UUID de la acta (formato: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

**Respuesta:**
```json
{
  "message": "OK",
  "estado": "pendiente_otp"
}
```

### 9. Registrar OTP y Firmar
```
POST /actas/{uuid}/registerotp/
```
**Parámetros URL:**
- `uuid`: UUID de la acta

**Headers:**
```
Content-Type: application/json
```
**Body:**
```json
{
  "otp": 123456,
  "ip": "192.168.1.1",
  "latitude": -34.6037,
  "longitude": -58.3816,
  "accuracy": "10m",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
```
**Respuesta:**
```json
{
  "message": "Acta firmada exitosamente",
  "estado": "pendiente_blockchain",
  "hash_documento": "abc123..."
}
```

### 10. Callback Blockchain (BFA Response)
```
POST /actas/{uuid}/bfaresponse/
```
**Parámetros URL:**
- `uuid`: UUID de la acta

**Headers:**
```
Content-Type: application/json
```
**Body:**
```json
{
  "status": "success"
}
```
o
```json
{
  "status": "failure"
}
```
**Respuesta:**
```json
{
  "message": "Resultado BFA guardado exitosamente",
  "estado": "firmada"
}
```

### 11. Rechazar Acta
```
POST /actas/{uuid}/reject/
```
**Parámetros URL:**
- `uuid`: UUID de la acta

**Headers:**
```
Content-Type: application/json
```
**Body:**
```json
{
  "motivo": "Error en los datos del acta"
}
```
**Respuesta:**
```json
{
  "message": "Acta rechazada exitosamente",
  "estado": "rechazada"
}
```

---

## 🎓 Endpoints de TÍTULOS

### 12. Recibir Título
```
POST /titulos/recibir/
```
**Headers:**
```
Content-Type: multipart/form-data
```
**Form Data:**
- `filename`: DNI/Lugar/SECTOR/CARRERA/MODO/PLAN (ej: `8205853/10/3/16/2/8707`)
  - **Formato requerido**: 6 componentes separados por `/`
  - **Componentes**: Todos deben ser numéricos
  - **Ejemplo válido**: `8205853/10/3/16/2/8707`
- `serie`: `títulos` (nombre de la serie)
- `doctype`: `títulos` (nombre del tipo de documento)
- `file`: Archivo PDF del título (requerido, debe ser PDF)
- `json_data`: (opcional) JSON string con datos adicionales:
  ```json
  {
    "DNI": "8205853",
    "Tipo DNI": "DNI",
    "Lugar": "10",
    "Facultad": "3",
    "Carrera": "16",
    "Modalidad": "2",
    "Plan": "8707",
    "Título": "Abogado"
  }
  ```

**Integración con Athento:**

Este endpoint envía el título a la API de Athento para su creación. Los detalles técnicos son:

- **Endpoint de Athento**: `POST {ATHENTO_BASE_URL}/api/v1/file/`
  - **URL Base**: `https://ucasal-uat.athento.com` (configurable)
  - **Documentación interactiva**: `https://ucasal-uat.athento.com/api/v1/explorer/?application=file&endpoint=file_create`
- **Autenticación**: Basic Auth
  - Usuario: Configurado en `athento.api.user`
  - Contraseña: Configurada en `athento.api.password`
- **Formato de envío**: `multipart/form-data`
- **Metadatos enviados**: Se envían automáticamente con prefijo `metadata.`:
  - `metadata.titulo_tipo_dni`
  - `metadata.titulo_dni`
  - `metadata.titulo_lugar`
  - `metadata.titulo_lugar_id`
  - `metadata.titulo_facultad`
  - `metadata.titulo_facultad_id`
  - `metadata.titulo_carrera`
  - `metadata.titulo_carrera_id`
  - `metadata.titulo_modalidad`
  - `metadata.titulo_modalidad_id`
  - `metadata.titulo_plan`
  - `metadata.titulo_titulo`

**Respuesta exitosa (201):**
```json
{
  "success": true,
  "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "filename": "8205853/10/3/16/2/8707",
  "doctype": "títulos",
  "serie": "títulos"
}
```

**Errores posibles:**
- `400`: Validación fallida (filename inválido, archivo no PDF, campos faltantes)
- `500`: Error en comunicación con Athento o procesamiento interno

### 13. Generar Código QR para Título
```
POST /titulos/qr/
```
**Headers:**
```
Content-Type: application/json
```
**Body:**
```json
{
  "url": "https://www.ucasal.edu.ar/validar/titulo/test-uuid"
}
```
**Respuesta:** Imagen PNG del código QR

### 14. Informar Estado del Título
```
POST /titulos/{uuid}/estado/
```
**Parámetros URL:**
- `uuid`: UUID del título

**Headers:**
```
Content-Type: application/json
```
**Body:**
```json
{
  "estado": "Aprobado por UA",
  "observaciones": "Título aprobado correctamente"
}
```
**Estados posibles:**
- `Recibido`
- `Pendiente Aprobación UA`
- `Aprobado por UA`
- `Pendiente Aprobación R`
- `Aprobado por R`
- `Pendiente Firma SG`
- `Firmado por SG`
- `Título Emitido` (flujo directo desde Firmado por SG, sin blockchain)
- `Rechazado`

**NOTA:** Los estados `Pendiente Blockchain` y `Registrado en Blockchain` están **SUSPENDIDOS temporalmente**. 
El flujo actual es: `Firmado por SG` → `Título Emitido` (sin blockchain). Se implementará firma digital en su lugar.

**Respuesta:**
```json
{
  "success": true,
  "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "estado": "Aprobado por UA",
  "estado_codigo": 2
}
```

### 15. Validar OTP para Título
```
POST /titulos/{uuid}/validar-otp/
```
**Parámetros URL:**
- `uuid`: UUID del título

**Headers:**
```
Content-Type: application/json
```
**Body:**
```json
{
  "otp": 123456,
  "usuario": "usuario@ucasal.edu.ar"
}
```
**Respuesta:**
```json
{
  "otp_valido": true,
  "usuario": "usuario@ucasal.edu.ar",
  "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### 16. Callback Blockchain para Título ⚠️ SUSPENDIDO
```
POST /titulos/{uuid}/bfaresponse/
```

**⚠️ NOTA IMPORTANTE:** Este endpoint está **SUSPENDIDO temporalmente**. 
La funcionalidad de blockchain para títulos ha sido deshabilitada. Se implementará firma digital en su lugar.

**Parámetros URL:**
- `uuid`: UUID del título

**Headers:**
```
Content-Type: application/json
```

**Respuesta (cuando está suspendido):**
```json
{
  "error": "Endpoint suspendido",
  "message": "El endpoint de blockchain para títulos está suspendido temporalmente. Se implementará firma digital en su lugar.",
  "status": "blockchain_suspended"
}
```
**Status Code:** `503 Service Unavailable`

**Documentación histórica (cuando estaba activo):**
- Body esperado: `{"status": "success"}` o `{"status": "failure"}`
- Respuesta anterior: `"Resultado BFA guardado exitosamente"`

---

## 📊 Resumen de Endpoints

| # | Método | Endpoint | Descripción |
|---|--------|----------|-------------|
| 1 | POST | `/api/auth/login/` | Obtener token JWT |
| 2 | POST | `/api/auth/refresh/` | Refrescar token JWT |
| 3 | GET | `/` | Información de API |
| 4 | GET | `/docs/` | Documentación |
| 5 | GET | `/admin/` | Panel admin |
| 6 | POST | `/actas/qr/` | Generar QR acta |
| 7 | POST | `/actas/getconfig/` | Obtener configuración |
| 8 | POST | `/actas/{uuid}/sendotp/` | Enviar OTP |
| 9 | POST | `/actas/{uuid}/registerotp/` | Registrar OTP y firmar |
| 10 | POST | `/actas/{uuid}/bfaresponse/` | Callback blockchain acta |
| 11 | POST | `/actas/{uuid}/reject/` | Rechazar acta |
| 12 | POST | `/titulos/recibir/` | Recibir título PDF |
| 13 | POST | `/titulos/qr/` | Generar QR título |
| 14 | POST | `/titulos/{uuid}/estado/` | Informar estado título |
| 15 | POST | `/titulos/{uuid}/validar-otp/` | Validar OTP título |
| 16 | POST | `/titulos/{uuid}/bfaresponse/` | Callback blockchain título |

---

## 🔑 Autenticación

La mayoría de endpoints requieren autenticación mediante Bearer Token:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Nota:** Algunos endpoints básicos (como `/`, `/docs/`, `/actas/qr/`) no requieren autenticación.

---

## 📝 Formato de UUID

Todos los endpoints que requieren UUID esperan el formato:
```
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Ejemplo:
```
a0a37fd1-e57e-482a-a745-bcfd8553bffb
```

---

## ⚠️ Notas Importantes

1. **Endpoints que requieren servicios externos:**
   - `/titulos/recibir/` - Requiere conexión con Athento
   - `/actas/{uuid}/registerotp/` - Requiere servicio UCASAL para validar OTP
   - `/titulos/{uuid}/estado/` - Requiere servicio UCASAL
   - `/titulos/{uuid}/validar-otp/` - Requiere servicio UCASAL
   - Callbacks blockchain - Requieren servicio UCASAL

2. **Content-Type:**
   - JSON: `Content-Type: application/json`
   - Form-data: `Content-Type: multipart/form-data`

3. **Códigos de respuesta comunes:**
   - `200` - OK
   - `201` - Created
   - `400` - Bad Request
   - `401` - Unauthorized
   - `404` - Not Found
   - `500` - Internal Server Error

---

## 🧪 Scripts de Prueba

Para probar los endpoints, puedes usar:

1. **Pruebas básicas:**
   ```bash
   python test_api_simple.py
   ```

2. **Pruebas avanzadas de actas:**
   ```bash
   python test_api_avanzado.py
   ```

3. **Pruebas de títulos:**
   ```bash
   python test_titulos_api.py
   ```

4. **Crear datos de prueba:**
   ```bash
   python crear_actas_prueba.py
   python crear_titulos_prueba.py
   ```

---

**Última actualización:** 2025-01-31
**Versión:** 1.0.0


