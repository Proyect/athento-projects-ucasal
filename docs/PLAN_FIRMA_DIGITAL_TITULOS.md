# Plan de Implementación: Firma Digital para Títulos

## Objetivo

Implementar sistema de firma digital para títulos, reemplazando la funcionalidad de blockchain suspendida. El flujo será: `Firmado por SG` → `Título Emitido` con PDF firmado digitalmente.

## Flujo Propuesto

```
Recibido
  ↓
Pendiente Aprobación UA
  ↓
Aprobado por UA
  ↓
Pendiente Aprobación R
  ↓
Aprobado por R
  ↓
Pendiente Firma SG
  ↓
[FIRMA DIGITAL] ← Endpoint nuevo: POST /titulos/{uuid}/firmar/
  ↓
Firmado por SG
  ↓
Título Emitido
```

## Componentes a Implementar

### 1. Endpoint de Firma Digital

**Endpoint**: `POST /titulos/{uuid}/firmar/`

**Ubicación**: `endpoints/titulos/titulos.py`

**Funcionalidad**:
- Validar que el título está en estado "Pendiente Firma SG"
- Validar OTP (si se requiere)
- Generar URL de validación
- Obtener QR de validación
- Incrustar QR e información en PDF
- Actualizar PDF en Athento
- Cambiar estado a "Firmado por SG"
- Guardar metadata de firma

**Body esperado**:
```json
{
  "otp": 123456,  // Opcional si se requiere OTP
  "ip": "192.168.1.1",
  "latitude": -34.6037,
  "longitude": -58.3816,
  "accuracy": "10m",
  "user_agent": "Mozilla/5.0..."
}
```

**Respuesta**:
```json
{
  "success": true,
  "message": "Título firmado exitosamente",
  "uuid": "xxx",
  "estado": "Firmado por SG",
  "fecha_firma": "2024-01-15T10:30:00"
}
```

### 2. Implementación de Firma PDF

**Opción A: Usar PyMuPDF (Recomendado)**

```python
import fitz  # PyMuPDF

def firmar_pdf_titulo(pdf_path, qr_info, firma_info):
    """
    Incrusta QR e información de firma en el PDF del título.
    
    Args:
        pdf_path: Path al PDF original
        qr_info: QRInfo con imagen y texto del QR
        firma_info: Dict con información de firma (firmante, fecha, etc.)
    
    Returns:
        BytesIO con el PDF firmado
    """
    doc = fitz.open(pdf_path)
    
    # Obtener primera página
    page = doc[0]
    
    # Insertar imagen QR
    rect_qr = fitz.Rect(qr_info.x, qr_info.y, 
                       qr_info.x + qr_info.width, 
                       qr_info.y + qr_info.height)
    page.insert_image(rect_qr, filename=qr_info.image_path)
    
    # Insertar texto de firma
    texto_firma = f"""Firmado digitalmente por:
{firma_info['firmante']}
Fecha: {firma_info['fecha']}
{firma_info.get('observaciones', '')}"""
    
    punto_texto = fitz.Point(qr_info.x, qr_info.y + qr_info.height + 20)
    page.insert_text(punto_texto, texto_firma, fontsize=10)
    
    # Guardar en BytesIO
    pdf_bytes = doc.tobytes()
    doc.close()
    
    return io.BytesIO(pdf_bytes)
```

**Opción B: Implementar SpPdfSimpleSigner Real**

Modificar `ucasal/mocks/sp_pdf_otp_simple_signer.py` para implementación real usando PyMuPDF.

### 3. Información a Incrustar

**QR Code**:
- URL de validación del título
- Formato: `https://www.ucasal.edu.ar/validar/index.php?d=titulo&uuid={uuid}`

**Texto de Firma**:
```
Firmado digitalmente por:
Secretaría General - UCASAL
Fecha: {fecha_firma}
Título: {titulo}
DNI: {dni}
```

**Metadata a Guardar**:
- `firmada.digital`: "1"
- `firma.fecha`: fecha de firma
- `firma.firmante`: "Secretaría General"
- `firma.ip`: IP de firma (opcional)
- `firma.url_validacion`: URL del QR

### 4. Integración con Flujo Existente

**Modificar**: `endpoints/titulos/titulos.py`

- Agregar función `firmar_titulo(request, uuid)`
- Reutilizar lógica de `UcasalServices` para QR y URLs
- Usar `UcasalConfig.titulo_validation_url_template()` para URL de validación

**Validaciones**:
- Estado debe ser "Pendiente Firma SG"
- OTP válido (si se requiere)
- PDF debe existir
- Doctype debe ser "títulos"

### 5. Notificaciones

**Template**: `ucasal_titulo_listo_firma.html`
- Notificar a SG cuando título está listo para firma

**Template**: `ucasal_titulo_firmado.html` (nuevo)
- Notificar cuando título ha sido firmado

## Dependencias

### Bibliotecas Requeridas

```python
# requirements.txt
PyMuPDF>=1.23.0  # Para manipulación de PDFs
# O alternativamente:
# PyPDF2>=3.0.0
```

### Servicios Requeridos

- Servicio UCASAL para acortar URLs
- Servicio UCASAL para generar QR
- Servicio UCASAL para validar OTP (si se requiere)

## Testing

### Tests Unitarios

1. Test de firma exitosa
2. Test de validación de estado
3. Test de validación de OTP
4. Test de incrustación de QR
5. Test de actualización de PDF

### Tests de Integración

1. Flujo completo desde "Pendiente Firma SG" hasta "Firmado por SG"
2. Validación de PDF generado
3. Verificación de QR en PDF

## Consideraciones

### Seguridad

- Validar permisos de firma
- Registrar IP y user agent
- Validar OTP si se requiere
- Logging de todas las firmas

### Performance

- Procesar PDFs en background si son muy grandes
- Cachear imágenes QR si es posible
- Optimizar tamaño de PDF generado

### Compatibilidad

- Mantener compatibilidad con PDFs existentes
- Validar que PDFs generados son legibles
- Asegurar que QR es escaneable

## Cronograma Estimado

1. **Fase 1**: Implementar firma básica (1-2 días)
   - Endpoint de firma
   - Incrustación de QR
   - Cambio de estado

2. **Fase 2**: Mejoras y validaciones (1 día)
   - Validaciones adicionales
   - Manejo de errores
   - Logging

3. **Fase 3**: Testing (1 día)
   - Tests unitarios
   - Tests de integración
   - Validación manual

4. **Fase 4**: Documentación (0.5 días)
   - Actualizar documentación de API
   - Guía de uso

**Total estimado**: 3.5-4.5 días

## Próximos Pasos Inmediatos

1. Decidir si se requiere OTP para firma de títulos
2. Instalar PyMuPDF o biblioteca elegida
3. Implementar función de incrustación de QR
4. Crear endpoint de firma
5. Integrar con flujo de estados
6. Testing



















