# Firma Digital con Athento - Documentación Técnica

## Resumen Ejecutivo

Este documento describe la metodología de implementación de firma digital para títulos en el sistema UCASAL usando Athento. La funcionalidad de blockchain ha sido suspendida temporalmente y se implementará firma digital en su lugar.

## Estado Actual

### Blockchain Suspendido
- Los estados `Pendiente Blockchain` y `Registrado en Blockchain` están suspendidos
- El endpoint `/titulos/{uuid}/bfaresponse/` retorna `503 Service Unavailable`
- Flujo actual: `Firmado por SG` → `Título Emitido` (sin blockchain)

### Implementación de Referencia: Actas

El sistema de actas ya implementa firma digital usando OTP. Esta implementación sirve como referencia para títulos.

## Análisis de la Implementación Actual (Actas)

### Componentes Principales

#### 1. SpPdfSimpleSigner
**Ubicación**: `ucasal/mocks/sp_pdf_otp_simple_signer.py`

```python
class SpPdfSimpleSigner:
    def sign(self, input_pdf_path, qr_info, otp_info):
        # Incrusta QR e información OTP en el PDF
        return io.BytesIO(b"mocked_pdf_content")
```

**Funcionalidad**:
- Recibe el path del PDF original
- Recibe información del QR (imagen, texto, posición)
- Recibe información del OTP (email, IP, GPS, user agent)
- Retorna un stream de bytes con el PDF firmado

**Nota**: Actualmente es un mock. La implementación real debe:
- Abrir el PDF original
- Incrustar imagen QR en posición especificada
- Agregar texto con información de firma
- Guardar el PDF modificado

#### 2. Proceso de Firma en Actas

**Endpoint**: `POST /actas/{uuid}/registerotp/`

**Flujo**:
1. Validar OTP con servicio UCASAL
2. Generar URL de validación y acortarla
3. Obtener imagen QR del servicio UCASAL
4. Crear `QRInfo` con imagen y texto
5. Crear `OTPInfo` con datos de firma
6. Llamar a `SpPdfSimpleSigner.sign()` para incrustar en PDF
7. Actualizar binario del documento en Athento
8. Marcar como firmado con feature `firmada.con.OTP`

**Código relevante** (`endpoints/actas/actas.py`, líneas 313-350):
```python
# Obtener QR image
url_to_shorten = UcasalConfig.acta_validation_url_template().replace('{{uuid}}', str(fil.uuid))
short_url = UcasalServices.get_short_url(auth_token=auth_token, url=url_to_shorten)
qr_stream = UcasalServices.get_qr_image(url=short_url)

# Generar QR info
qr_info = QRInfo(
    image_path=qr_image_tmp_path,
    image_text=f"Firmado con OTP por:\r\n{nombre_docente}\r\n{mail_docente_ofuscado}\r\n{fecha_firma}",
    x=10, y=10, width=40, height=40
)

# Generar OTP info
otp_info = OTPInfo(mail=mail_docente_ofuscado, ip=ip, latitude=latitude, 
                   longitude=longitude, accuracy=accuracy, user_agent=user_agent)

# Incrustar QR y OTP en el pdf
signer = SpPdfSimpleSigner()
pdf_out_stream = signer.sign(input_pdf_path=fil.file.path, qr_info=qr_info, otp_info=otp_info)

# Actualizar binario
fil.update_binary(FileObject(pdf_temp), fil.filename + ".pdf")
fil.set_feature('firmada.con.OTP', "1")
```

## Metodología de Firma Digital

### Opciones de Implementación

#### Opción 1: Firma Digital Simple (Similar a Actas)
- Incrustar QR con URL de validación
- Agregar información de firma (firmante, fecha, IP, GPS)
- No requiere certificado digital
- Similar a la implementación actual de actas

**Ventajas**:
- Implementación rápida
- Reutiliza código existente
- No requiere certificados

**Desventajas**:
- No es una firma digital certificada
- Solo agrega metadatos visuales

#### Opción 2: Firma Digital Certificada
- Usar biblioteca de firma digital (ej: PyPDF2, reportlab, PyMuPDF)
- Incrustar certificado digital en el PDF
- Crear campo de firma visible
- Validar certificado

**Ventajas**:
- Firma digital legalmente válida
- Certificado verificable
- Cumple estándares internacionales

**Desventajas**:
- Requiere certificado digital
- Implementación más compleja
- Requiere gestión de certificados

#### Opción 3: Integración con Athento
- Usar APIs de Athento para firma digital
- Athento gestiona certificados
- Integración nativa con el sistema

**Ventajas**:
- Integración nativa
- Gestión centralizada de certificados
- Funcionalidades avanzadas de Athento

**Desventajas**:
- Requiere investigación de APIs de Athento
- Dependencia de Athento

### Recomendación

**Fase 1 (Inmediata)**: Implementar Opción 1 (Firma Digital Simple)
- Reutilizar código de actas
- Adaptar para títulos
- Rápida implementación

**Fase 2 (Futuro)**: Evaluar Opción 2 o 3
- Investigar APIs de Athento para firma certificada
- Evaluar necesidad de certificados digitales
- Implementar según requerimientos legales

## Investigación sobre Athento

### APIs de Athento para Firma Digital

Según la documentación de Athento:
- **API Explorer**: `https://subdominio.athento.com/api/v1/explorer/`
- **Autenticación**: Basic Auth o OAuth
- **Documentación**: Disponible en la interfaz de Athento

### Endpoints Relevantes

1. **File Create**: `POST /api/v1/file/`
   - Ya implementado para recibir títulos
   - Permite subir documentos con metadata

2. **File Update**: `PUT /api/v1/file/{uuid}/`
   - Actualizar documento
   - Modificar metadata

3. **Document Signing** (a investigar):
   - Buscar endpoints relacionados con firma
   - Verificar si Athento tiene funcionalidad nativa de firma

### Próximos Pasos de Investigación

1. Acceder al API Explorer de Athento UAT
2. Buscar endpoints relacionados con:
   - Firma de documentos
   - Certificados digitales
   - Validación de firmas
3. Revisar documentación de Athento sobre firma digital
4. Consultar con soporte de Athento si es necesario

## Plan de Implementación para Títulos

### Flujo Propuesto

1. **Título en estado "Pendiente Firma SG"**
   - Sistema notifica a Secretaría General
   - SG accede al título para firmar

2. **Proceso de Firma**
   - SG ingresa OTP (si se requiere)
   - Sistema genera URL de validación
   - Sistema obtiene QR de validación
   - Sistema incrusta QR e información en PDF
   - Sistema actualiza PDF en Athento

3. **Cambio de Estado**
   - Estado cambia a "Firmado por SG"
   - Feature `firmada.con.OTP` o `firmada.digital` = "1"
   - Fecha de firma guardada

4. **Emisión**
   - Estado cambia a "Título Emitido"
   - PDF firmado está listo para emisión

### Información a Incrustar en PDF

- **QR Code**: URL de validación del título
- **Texto de Firma**:
  - Firmante: Secretaría General
  - Fecha y hora de firma
  - IP de firma (opcional)
  - Información adicional según requerimientos

### Comparación con Actas

| Aspecto | Actas | Títulos (Propuesto) |
|---------|-------|---------------------|
| Firmante | Docente | Secretaría General |
| OTP | Requerido | A definir |
| QR | Sí | Sí |
| Información GPS | Sí | Opcional |
| Validación | URL de acta | URL de título |
| Estado final | Firmada | Firmado por SG → Emitido |

## Bibliotecas Python para Firma Digital

### Opciones Disponibles

1. **PyPDF2** / **PyPDF4**
   - Manipulación de PDFs
   - Agregar campos de firma
   - No incluye firma certificada

2. **PyMuPDF (fitz)**
   - Manipulación avanzada de PDFs
   - Agregar imágenes y texto
   - Mejor rendimiento

3. **reportlab**
   - Generación de PDFs
   - Agregar elementos visuales
   - No para modificar PDFs existentes

4. **endesive** / **pyHanko**
   - Firma digital certificada
   - Estándares PKCS#7, PAdES
   - Requiere certificado

### Recomendación para Implementación Inicial

**PyMuPDF (fitz)** para incrustar QR e información:
- Fácil de usar
- Buen rendimiento
- Permite agregar imágenes y texto
- No requiere certificado (firma simple)

## Próximos Pasos

1. ✅ **Completado**: Suspender blockchain
2. ✅ **Completado**: Documentar metodología
3. ⏳ **Pendiente**: Investigar APIs de Athento para firma
4. ⏳ **Pendiente**: Implementar SpPdfSimpleSigner real (o usar PyMuPDF)
5. ⏳ **Pendiente**: Crear endpoint de firma para títulos
6. ⏳ **Pendiente**: Integrar con flujo de estados
7. ⏳ **Pendiente**: Testing y validación

## Referencias

- [Athento API Documentation](https://soporte.athento.com/hc/es/articles/360007937694-Recursos-para-usar-la-API-de-Athento-e-integrarlo-con-otra-aplicación)
- Implementación de actas: `endpoints/actas/actas.py`
- Mock de firma: `ucasal/mocks/sp_pdf_otp_simple_signer.py`
- Servicios UCASAL: `external_services/ucasal/ucasal_services.py`



















