class QRInfo:
    def __init__(self, image_path, image_text, x, y, width, height):
        pass
class OTPInfo:
    def __init__(self, mail, ip, latitude, longitude, accuracy, user_agent):
        pass
class SpPdfSimpleSigner:
    def sign(self, input_pdf_path, qr_info, otp_info):
        import io
        return io.BytesIO(b"mocked_pdf_content")
