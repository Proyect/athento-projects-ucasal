# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from django.utils.translation import gettext as _
from django.http import HttpResponse
from ucasal2.utils import DesignacionesStates
from ucasal2.external_services.ucasal.designaciones_services import DesignacionesServices
from ucasal2.external_services.ucasal.ucasal_services import UcasalServices
from ucasal2.utils import is_digit, is_non_empty_string, get_mail_for_otp, get_arg_time, get_pdf_hash
from custom.sp_libs.python.sp_pdf_otp_simple_signer.sp_pdf_otp_simple_signer import SpPdfSimpleSigner, QRInfo, OTPInfo
from ucasal2.utils import UcasalConfig
from file.models import File
from django.core.files import File as DjangoFile
from core.exceptions import AthentoseError
from django.contrib.auth.models import Group
from django_currentuser.middleware import get_current_user
from datetime import datetime
import base64
import locale
import io
import os

class FirmaDesignacionesVR(DocumentOperation):
    version = "1.0"
    name = _("FirmaDesignacionesVR")
    description = _("Firma la Designacion por parte del VR")
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose","FirmaDesignacionesVR")

    def execute(self, *args, **kwargs):
        flogger: SpFeatureLogger = NullSpFeatureLogger()     
        btn_firmar = None
        try:
            logger = self._logger
            logger.entry()

            fil = self.document
            uuid = str(fil.uuid)
            lifecycle_state = fil.life_cycle_state.name
            flogger = SpFeatureLogger.getLogger(fil)

            # Bloquea el boton y codigo otp mientras se procesa la operacion
            try:
                btn_firmar = fil.get_metadata('metadata.designaciones_firmar')
                if btn_firmar:
                    btn_firmar.locked = True
                    btn_firmar.save()                
            except Exception:
                logger.warning("No se pudo bloquear el boton de firma.")

            if (lifecycle_state == DesignacionesStates.pendiente_firma_otp):

                fil.set_feature('lfstate', lifecycle_state)

                # 1) OTP
                otp = str(fil.gmv('metadata.designaciones_otp') or '').strip()
                if otp == '':
                    return logger.exit({"msg": f"El OTP no puede ser nulo, ingrese un valor válido", "msg_type": "warning"})
                    #return AthentoseError({'msg': "El OTP no puede ser nulo, ingrese un valor válido", 'msg_type': 'error'})                    
                if not is_digit(otp):                    
                    return logger.exit({"msg": f"'OTP' debe ser un número entero positivo en lugar de '{otp}'", "msg_type": "warning"})
                    #raise AthentoseError(f"'OTP' debe ser un número entero positivo en lugar de '{otp}'")
                otp = int(otp)

                # 2) Datos del VR (grupo)                
                usuario = get_current_user()                

                if not get_current_user().groups.filter(name='Vicerrector Administrativo').exists():                  
                    return logger.exit({"msg": f"El usuario loguerado no pertenece al grupo 'Vicerrector Administrativo'", "msg_type": "error"})

                mail_vr = usuario.email or ""
                nombre_vr = f"{usuario.first_name or ''} {usuario.last_name or ''}".strip()

                if not is_non_empty_string(mail_vr):
                    return logger.exit({"msg": f"El mail del Vicerrector Administrativo no se pudo obtener del grupo", "msg_type": "error"})
                    #return AthentoseError("El mail del Vicerrector Administrativo no se pudo obtener del grupo")

                # 3) Validar OTP con UCASAL       
                try:
                    UcasalServices.validate_otp(user=mail_vr, otp=otp)
                except AthentoseError:                    
                    return logger.exit({
                        "msg": "OTP inválido. Verifique el código ingresado",
                        "msg_type": "warning"
                    })

                fil.set_feature('valide_otp', '1')

                #UcasalServices.validate_otp(user=mail_vr, otp=otp)
                #print("Resultado validación OTP:", result)
                #fil.set_feature('valide_otp', '1')

                # 4) Obtener token + URL pública + QR 
                auth_token = UcasalServices.get_auth_token(
                    user=UcasalConfig.token_svc_user(),
                    password=UcasalConfig.token_svc_password()
                )
                fil.set_feature('obtuve_auth_token', '1')

                url_to_shorten = UcasalConfig.designaciones_validation_url_template().replace('{{uuid}}', uuid)
                short_url = UcasalServices.get_short_url(auth_token=auth_token, url=url_to_shorten)

                qr_stream = UcasalServices.get_qr_image(url=short_url)
                b64_qr = base64.b64encode(qr_stream).decode('utf-8')

                # 5) Datos de la firma 
                mail_vr_ofuscado = get_mail_for_otp(mail_vr)
                fecha_firma_texto = get_arg_time()

                try:
                    locale.setlocale(locale.LC_TIME, 'es_AR.UTF-8')
                except Exception:
                    pass
                now = datetime.now()
                day = now.strftime("%d")
                month = now.strftime("%B")
                year = now.strftime("%Y")

                firmada_con_otp = fil.gfv('firmada_con_otp')
                if firmada_con_otp == "1":
                    logger.debug({"msg": f"La Designacion {uuid} ya se encuentra firmada", "msg_type": "warning"})
                else:
                    logger.debug('Firmando PDF existente con OTP...')

                    # ======== FIRMA SOBRE PDF EXISTENTE ========

                    # 5.a) Leer bytes del PDF actual desde el path
                    with open(fil.path(), "rb") as f:
                        current_bytes = f.read()
                    if not current_bytes:
                        return AthentoseError("El documento no tiene binario para firmar")

                    # 5.b) Guardar QR como PNG temporal (para QRInfo.image_path)
                    qr_image_tmp_path = f"/var/www/athentose/media/tmp/ucasal2_qr_{fil.uuid}.png"
                    os.makedirs(os.path.dirname(qr_image_tmp_path), exist_ok=True)
                    with open(qr_image_tmp_path, "wb") as qr_file:
                        qr_file.write(qr_stream)

                    # 5.c) Texto junto al QR 
                    qr_text = (                        
                        "Firmado con OTP por:\r\n"
                        f"{nombre_vr}\r\n"
                        f"{mail_vr_ofuscado}\r\n"
                        f"{fecha_firma_texto}"
                    )

                    # 5.d) QRInfo usando image_path + image_text 
                    qr_info = QRInfo(
                        image_path=qr_image_tmp_path,
                        image_text=qr_text,                        
                        #x=845, y=20, width=75, height=75  # ajustá posición/tamaño
                        x=845, y=11, width=70, height=70  # ajustá posición/tamaño
                    )

                    # 5.e) OTPInfo — AJUSTE A DESIGNACIONES (mail + metadatos opcionales)
                    otp_info = OTPInfo(
                        mail="\n" + mail_vr_ofuscado,
                        ip="N/A",
                        latitude=0.0,
                        longitude=0.0,
                        accuracy="N/A",
                        user_agent="Athentose/Signer"
                    )
                    

                    # 5.f) Firmar y actualizar el binario
                    signer = SpPdfSimpleSigner()

                    signed_result = signer.sign(
                        fil.path(),   
                        qr_info,      
                        otp_info      
                    )

                    # Signer devuelve io.BytesIO
                    signed_pdf_bytes = signed_result.getvalue()

                    document = DjangoFile(io.BytesIO(signed_pdf_bytes), f"{fil.filename}.pdf")
                    fil.update_binary(document)

                    # 5.g) Features finales 
                    fil.set_feature('firmada_con_otp', "1")
                    
                    # Guardamos los datos para el PDF (con el QR)
                    body_to_save = {
                        'fecha_firma': {'day': day, 'month': month, 'year': year},
                        'qr_data': {'qr_base64': b64_qr},
                        'qr_text': {
                            'firmado_por': 'Firmado con OTP por:',
                            'nombre_vr': nombre_vr,
                            'mail_vr': mail_vr_ofuscado,
                            'fecha_firma': fecha_firma_texto
                        }
                    }

                    # No guardamos el Base64 en la base de datos para evitar error de indice (8191 bytes)
                    # fil.set_feature('bodyFinal', body_to_save) # Línea original comentada
                    body_to_save['qr_data'].pop('qr_base64', None)
                    fil.set_feature('bodyFinal', body_to_save)

                    fil.set_metadata('metadata.designaciones_usuario_firmante', nombre_vr, overwrite=True)

                    logger.debug({"msg": f"La Designacion {uuid} fue firmada exitosamente sobre el PDF existente", "msg_type": "success"})                    


            # =========================================
            # Registrar en BFA
            # =========================================
            registrada_en_blockchain = fil.gfv('registro_blockchain')
            if registrada_en_blockchain == 'pending':
                raise AthentoseError('La designación ya había sido enviada a blockchain y su resultado aún está pendiente')
            if registrada_en_blockchain == 'success':
                raise AthentoseError('La designación ya está registrada en blockchain')
            pdf_hash = get_pdf_hash(fil)
            callback_url = DesignacionesServices.set_callback_url(uuid=uuid)
            ok_response_text = UcasalServices.register_in_blockchain(
                auth_token=auth_token,
                hash=pdf_hash,
                file_uuid=str(fil.uuid),
                callback_url=callback_url
            )
            fil.set_feature('ucasal2.svc.ok_response', ok_response_text)
            fil.set_feature('registro_blockchain', 'pending')
            response = DesignacionesServices.change_state_integration(uuid=uuid, state=4, auth_token=auth_token)
            fil.set_feature('Response estado 4', response.text)
            fil.set_feature('Status Code 4', response.status_code)
            if lifecycle_state == DesignacionesStates.pendiente_firma_otp:
                fil.change_life_cycle_state(DesignacionesStates.pendiente_blockchain)

            return logger.exit({'msg': 'Designación Firmada correctamente aguardando respuesta de Blockchain', 'msg_type': 'success'})
            
        except FileNotFoundError as e:
            flogger.error(f'Error al procesar el archivo: {str(e)}')
            return logger.exit({"msg": str(e), "msg_type": "error"}, exc_info=True)

        except AthentoseError as e:
            flogger.error(f'Error en la operación: {str(e)}')
            return logger.exit({"msg": str(e), "msg_type": "error"}, exc_info=True)

        except Exception as e:
            flogger.error(f'Error inesperado: {str(e)}')
            return logger.exit({"msg": str(e), "msg_type": "error"}, exc_info=True)


        finally:
            try:                
                if btn_firmar:
                    btn_firmar.locked = False
                    btn_firmar.save()
            except Exception:
                logger.warning("No se pudo desbloquear el boton de firma")


VERSION = FirmaDesignacionesVR.version
NAME = FirmaDesignacionesVR.name
DESCRIPTION = FirmaDesignacionesVR.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = FirmaDesignacionesVR.configuration_parameters

def run(uuid=None, **params):
    return FirmaDesignacionesVR(uuid, **params).run()
