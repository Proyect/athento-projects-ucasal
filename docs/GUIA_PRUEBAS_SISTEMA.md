# 🧪 Guía de Pruebas del Sistema UCASAL

## 📍 Estado del Servidor

- **URL Base**: http://localhost:8012
- **Estado**: ✅ Servidor corriendo

---

## 🚀 Formas de Probar el Sistema

### 1. Pruebas Manuales con Navegador

#### URLs que puedes abrir directamente en el navegador:

1. **Información de la API**
   ```
   http://localhost:8012/
   ```

2. **Documentación**
   ```
   http://localhost:8012/docs/
   ```

3. **Panel de Administración**
   ```
   http://localhost:8012/admin/
   ```
   - Usuario: `admin`
   - Contraseña: `admin123` (si no has creado otro usuario, ejecuta: `python manage.py createsuperuser`)

---

### 2. Pruebas con cURL (Terminal/PowerShell)

#### Obtener Token JWT

```bash
# Windows PowerShell
curl -X POST http://localhost:8012/api/auth/login/ `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"admin\",\"password\":\"admin123\"}'

# Linux/Mac
curl -X POST http://localhost:8012/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**Respuesta esperada:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### Usar Token en Requests

```bash
# Guardar token en variable (PowerShell)
$token = "TU_TOKEN_AQUI"

# Hacer request con token
curl -X GET http://localhost:8012/ `
  -H "Authorization: Bearer $token"
```

---

### 3. Pruebas con Postman/Insomnia

#### Configuración de Collection

1. **Crear Nueva Collection**: "UCASAL API"
2. **Variable de Entorno**: 
   - `base_url`: `http://localhost:8012`
   - `token`: (se llenará automáticamente después del login)

#### Requests a Configurar

##### 1. Login (Obtener Token)
- **Método**: POST
- **URL**: `{{base_url}}/api/auth/login/`
- **Headers**: `Content-Type: application/json`
- **Body** (JSON):
```json
{
  "username": "admin",
  "password": "admin123"
}
```
- **Tests** (Postman Script):
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

var jsonData = pm.response.json();
pm.environment.set("token", jsonData.access);
```

##### 2. Información de API
- **Método**: GET
- **URL**: `{{base_url}}/`
- **Headers**: Ninguno requerido

##### 3. Generar QR
- **Método**: POST
- **URL**: `{{base_url}}/actas/qr/`
- **Headers**: `Content-Type: application/json`
- **Body** (JSON):
```json
{
  "url": "https://www.ucasal.edu.ar/validar/acta/test-uuid"
}
```

##### 4. Obtener Configuración
- **Método**: POST
- **URL**: `{{base_url}}/actas/getconfig/`
- **Headers**: `Content-Type: application/json`
- **Body** (JSON):
```json
{
  "key": "test_key",
  "is_secret": false
}
```

---

### 4. Pruebas con Python Scripts

#### Script de Prueba Básico

Crea un archivo `test_api.py`:

```python
import requests
import json

BASE_URL = "http://localhost:8012"

# 1. Información de API
print("=" * 50)
print("1. Información de API")
print("=" * 50)
response = requests.get(f"{BASE_URL}/")
print(json.dumps(response.json(), indent=2))

# 2. Documentación
print("\n" + "=" * 50)
print("2. Documentación")
print("=" * 50)
response = requests.get(f"{BASE_URL}/docs/")
print(json.dumps(response.json(), indent=2))

# 3. Login
print("\n" + "=" * 50)
print("3. Login")
print("=" * 50)
response = requests.post(
    f"{BASE_URL}/api/auth/login/",
    json={"username": "admin", "password": "admin123"}
)
if response.status_code == 200:
    token_data = response.json()
    token = token_data.get("access")
    print(f"Token obtenido: {token[:50]}...")
    
    # 4. Usar token
    print("\n" + "=" * 50)
    print("4. Request con Token")
    print("=" * 50)
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/", headers=headers)
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Error en login: {response.status_code}")
    print(response.text)

# 5. Generar QR
print("\n" + "=" * 50)
print("5. Generar QR")
print("=" * 50)
response = requests.post(
    f"{BASE_URL}/actas/qr/",
    json={"url": "https://www.ucasal.edu.ar/test"}
)
if response.status_code == 200:
    print(f"QR generado: {len(response.content)} bytes")
    # Guardar imagen
    with open("qr_test.png", "wb") as f:
        f.write(response.content)
    print("Imagen guardada en qr_test.png")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

Ejecutar:
```bash
python test_api.py
```

---

### 5. Pruebas Interactivas con Django Shell

```bash
python manage.py shell
```

```python
# En el shell de Django
from endpoints.actas.models import Acta
import uuid
from django.contrib.auth.models import User

# Crear una acta de prueba
acta = Acta.objects.create(
    uuid=uuid.uuid4(),
    titulo="Acta de Prueba Manual",
    descripcion="Descripción de prueba",
    docente_asignado="profesor@test.com",
    nombre_docente="Prof. Test",
    codigo_sector="001",
    estado="recibida"
)

print(f"Acta creada: {acta}")
print(f"UUID: {acta.uuid}")
print(f"Estado: {acta.estado}")

# Verificar métodos
print(f"Puede firmar: {acta.puede_firmar()}")
print(f"Puede rechazar: {acta.puede_rechazar()}")

# Listar todas las actas
print("\nTodas las actas:")
for a in Acta.objects.all():
    print(f"  - {a.titulo} ({a.estado})")
```

---

### 6. Pruebas de Endpoints de Actas

#### Prueba Completa del Flujo de Acta

```python
import requests
import json
import uuid

BASE_URL = "http://localhost:8012"

# Primero necesitas crear una acta desde el admin o shell
# Vamos a asumir que ya tienes un UUID de acta
acta_uuid = "TU_UUID_AQUI"  # Reemplazar con UUID real

# 1. Enviar OTP
print("1. Enviando OTP...")
response = requests.post(f"{BASE_URL}/actas/{acta_uuid}/sendotp/")
if response.status_code == 200:
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)

# 2. Registrar OTP (requiere OTP válido del email)
print("\n2. Registrando OTP...")
response = requests.post(
    f"{BASE_URL}/actas/{acta_uuid}/registerotp/",
    json={
        "otp": 123456,  # Reemplazar con OTP real
        "ip": "192.168.1.1",
        "latitude": -34.6037,
        "longitude": -58.3816,
        "accuracy": "10m",
        "user_agent": "Mozilla/5.0"
    }
)
if response.status_code == 200:
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)

# 3. Respuesta Blockchain (simulación)
print("\n3. Simulando respuesta blockchain...")
response = requests.post(
    f"{BASE_URL}/actas/{acta_uuid}/bfaresponse/",
    json={"status": "success"}
)
print(f"Status: {response.status_code}")
print(response.text)
```

---

### 7. Pruebas de Endpoints de Títulos

#### Script Completo de Pruebas de Títulos

Crea un archivo `test_titulos_api.py` o usa el script incluido:

```python
import requests
import json

BASE_URL = "http://localhost:8012"

# 1. Generar QR para Título
print("1. Generando QR para título...")
response = requests.post(
    f"{BASE_URL}/titulos/qr/",
    json={"url": "https://www.ucasal.edu.ar/validar/titulo/test-uuid"}
)
if response.status_code == 200:
    print(f"QR generado: {len(response.content)} bytes")
    with open("qr_titulo_test.png", "wb") as f:
        f.write(response.content)
    print("Imagen guardada en qr_titulo_test.png")
else:
    print(f"Error: {response.status_code}")

# 2. Recibir Título (requiere archivo PDF real y conexión con Athento)
print("\n2. Recibiendo título...")
# Crear PDF de prueba simple
pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF'

files = {
    'file': ('titulo_test.pdf', pdf_content, 'application/pdf')
}
data = {
    'filename': '8205853/10/3/16/2/8707',  # DNI/Lugar/SECTOR/CARRERA/MODO/PLAN
    'serie': 'títulos',
    'doctype': 'títulos',
    'json_data': json.dumps({
        'DNI': '8205853',
        'Tipo DNI': 'DNI',
        'Lugar': '10',
        'Facultad': '3',
        'Carrera': '16',
        'Modalidad': '2',
        'Plan': '8707',
        'Título': 'Abogado'
    })
}

response = requests.post(
    f"{BASE_URL}/titulos/recibir/",
    files=files,
    data=data
)

if response.status_code in [200, 201]:
    data_resp = response.json()
    titulo_uuid = data_resp.get("uuid")
    print(f"Título recibido: {titulo_uuid}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
    print("Nota: Este endpoint requiere conexión con Athento")

# 3. Informar Estado (requiere UUID del título)
titulo_uuid = "TU_UUID_TITULO_AQUI"  # Reemplazar con UUID real
print("\n3. Informando estado...")
response = requests.post(
    f"{BASE_URL}/titulos/{titulo_uuid}/estado/",
    json={
        "estado": "Aprobado por UA",
        "observaciones": "Título aprobado correctamente"
    }
)
if response.status_code == 200:
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)
    print("Nota: Este endpoint requiere conexión con servicio UCASAL")

# 4. Validar OTP (requiere OTP válido del servicio UCASAL)
print("\n4. Validando OTP...")
response = requests.post(
    f"{BASE_URL}/titulos/{titulo_uuid}/validar-otp/",
    json={
        "otp": 123456,  # Reemplazar con OTP real
        "usuario": "usuario@ucasal.edu.ar"
    }
)
if response.status_code == 200:
    print(json.dumps(response.json(), indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)

# 5. Callback Blockchain
print("\n5. Simulando callback blockchain...")
response = requests.post(
    f"{BASE_URL}/titulos/{titulo_uuid}/bfaresponse/",
    json={"status": "success"}
)
print(f"Status: {response.status_code}")
print(response.text)
```

#### Scripts de Prueba Incluidos

1. **Crear títulos de prueba:**
   ```bash
   python crear_titulos_prueba.py
   ```
   Crea 4 títulos en diferentes estados para pruebas.

2. **Probar endpoints de títulos:**
   ```bash
   python test_titulos_api.py
   ```
   Prueba todos los endpoints de títulos con los datos creados.

---

## 📝 Checklist de Pruebas Recomendadas

### Tests Básicos (Sin necesidad de datos previos)

- [x] GET `/` - Información de API
- [x] GET `/docs/` - Documentación
- [x] POST `/api/auth/login/` - Autenticación
- [x] POST `/api/auth/refresh/` - Refresh token
- [x] POST `/actas/qr/` - Generar QR
- [x] POST `/actas/getconfig/` - Obtener configuración

### Tests de Actas (Requieren acta creada)

- [ ] POST `/actas/{uuid}/sendotp/` - Enviar OTP
- [ ] POST `/actas/{uuid}/registerotp/` - Registrar OTP
- [ ] POST `/actas/{uuid}/bfaresponse/` - Callback blockchain
- [ ] POST `/actas/{uuid}/reject/` - Rechazar acta

### Tests de Títulos (Requieren título recibido)

- [x] POST `/titulos/qr/` - Generar QR para título
- [ ] POST `/titulos/recibir/` - Recibir título (requiere Athento)
- [ ] POST `/titulos/{uuid}/estado/` - Informar estado (requiere servicio UCASAL)
- [ ] POST `/titulos/{uuid}/validar-otp/` - Validar OTP (requiere servicio UCASAL)
- [ ] POST `/titulos/{uuid}/bfaresponse/` - Callback blockchain (requiere servicio UCASAL)

---

## 🔧 Solución de Problemas Comunes

### El servidor no responde
```bash
# Verificar que el servidor está corriendo
# Abrir nueva terminal y ejecutar:
python manage.py runserver 8012
```

### Error 404 en endpoints
- Verificar que la URL está correcta
- Verificar que el servidor está corriendo
- Verificar que las migraciones están aplicadas: `python manage.py migrate`

### Error de autenticación
- Verificar que el usuario existe: `python manage.py createsuperuser`
- Verificar que el token no ha expirado (válido 1 hora)

### Error en tests con UUID
- Los UUIDs deben ser válidos
- Primero crear actas/títulos desde el admin o shell

---

## 📊 Herramientas Recomendadas

1. **Postman** o **Insomnia**: Para pruebas interactivas de API
2. **Django Admin**: Para crear datos de prueba
3. **Django Shell**: Para pruebas programáticas
4. **Browser DevTools**: Para inspeccionar requests/responses
5. **curl/HTTPie**: Para pruebas rápidas desde terminal

---

## 🎯 Próximos Pasos

1. **Crear datos de prueba** desde el admin o shell
2. **Probar endpoints básicos** (QR, getconfig, etc.)
3. **Probar autenticación JWT**
4. **Probar flujo completo de actas**
5. **Probar flujo completo de títulos**

¡Listo para probar! 🚀


