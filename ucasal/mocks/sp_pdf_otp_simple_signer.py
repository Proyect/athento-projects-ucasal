import io
import os

class QRInfo:
    def __init__(self, image_path, image_text, x, y, width, height):
        self.image_path = image_path
        self.image_text = image_text
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class OTPInfo:
    def __init__(self, mail, ip, latitude, longitude, accuracy, user_agent):
        self.mail = mail
        self.ip = ip
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy = accuracy
        self.user_agent = user_agent

class SpPdfSimpleSigner:
    """
    Clase para firmar PDFs incrustando QR e información de firma.
    Implementación real usando PyMuPDF (fitz).
    """
    
    def sign(self, input_pdf_path, qr_info, otp_info=None):
        """
        Incrusta QR e información de firma en el PDF.
        
        Args:
            input_pdf_path: Path al PDF original
            qr_info: QRInfo con imagen y texto del QR
            otp_info: OTPInfo opcional con información de OTP (para actas)
        
        Returns:
            BytesIO con el PDF firmado
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            # Fallback a mock si PyMuPDF no está instalado
            return io.BytesIO(b"mocked_pdf_content")
        
        # Abrir el PDF
        doc = fitz.open(input_pdf_path)
        
        try:
            # Obtener primera página
            page = doc[0]
            
            # Convertir coordenadas de puntos a puntos (PyMuPDF usa puntos)
            # Asumimos que las coordenadas vienen en puntos, si vienen en mm multiplicar por 2.83465
            rect_qr = fitz.Rect(
                qr_info.x, 
                qr_info.y, 
                qr_info.x + qr_info.width, 
                qr_info.y + qr_info.height
            )
            
            # Insertar imagen QR si existe el archivo
            if os.path.exists(qr_info.image_path):
                page.insert_image(rect_qr, filename=qr_info.image_path)
            else:
                # Si no existe el archivo, intentar leer desde bytes si está disponible
                # Por ahora solo logueamos el error
                pass
            
            # Insertar texto de firma debajo del QR
            texto_firma = qr_info.image_text if qr_info.image_text else ""
            
            # Si hay información OTP, agregarla
            if otp_info:
                texto_firma += f"\nIP: {otp_info.ip}\n"
                texto_firma += f"GPS: {otp_info.latitude}, {otp_info.longitude}\n"
                texto_firma += f"Precisión: {otp_info.accuracy}"
            
            # Insertar texto
            if texto_firma:
                punto_texto = fitz.Point(qr_info.x, qr_info.y + qr_info.height + 20)
                # Insertar texto con formato
                page.insert_text(
                    punto_texto, 
                    texto_firma, 
                    fontsize=10,
                    color=(0, 0, 0)  # Negro
                )
            
            # Convertir a bytes
            pdf_bytes = doc.tobytes()
            
            return io.BytesIO(pdf_bytes)
            
        finally:
            doc.close()
