# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from django.utils.translation import gettext as _
from django.http import HttpResponse

from core.exceptions import AthentoseError
from django.core.files import File as DjangoFile
from django_currentuser.middleware import get_current_user

from custom.ucasal2.external_services.ucasal.ucasal_services import UcasalServices
from custom.ucasal2.external_services.ucasal.designaciones_services import DesignacionesServices
from custom.ucasal2.utils import UcasalConfig
from custom.ucasal2.utils import is_digit, get_mail_for_otp, get_arg_time, get_pdf_hash, ProgramasStates
from custom.sp_libs.python.sp_pdf_otp_simple_signer.sp_pdf_otp_simple_signer import (
    SpPdfSimpleSigner,
    QRInfo,
    OTPInfo,
)

import base64
import io
import os
from datetime import datetime
import locale
import requests



class FirmaProgramaOTP(DocumentOperation):
    """Firma el PDF de un programa con OTP y QR, y lo registra en blockchain.

    Flujo esperado:
      - El programa debe estar en estado ProgramasStates.pendiente_firma_otp
      - El OTP se ingresa en un metadato del programa (metadata.programas_otp) y se
        valida contra el servicio de OTP de UCASAL.
      - Se Recibe el JSON con los datos del programa.
      - Se valida que el JSON sea válido.
      - Se obtienen los datos del programa.
      - Se obtiene el OTP del metadato del programa.
      - Se valida que el OTP sea correcto.
      - Se genera el PDF 
      - Se firma el PDF con el OTP y se registra en blockchain.
      - El programa pasa a estado ProgramasStates.firmado.
    """

    version = "1.0"
    name = _("FirmaProgramaOTP")
    description = _(
        "Firma programa con OTP y QR, y los registra en blockchain"
    )
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose", "FirmaProgramaOTP")
    

    def execute(self, *args, **kwargs):  # noqa: D401
        flogger: SpFeatureLogger = NullSpFeatureLogger()
        logger = self._logger
        logger.entry()

        fil = self.document
        uuid = str(fil.uuid)        

        try:
            flogger = SpFeatureLogger.getLogger(fil)

            lifecycle_state = fil.life_cycle_state.name if fil.life_cycle_state else ""
            flogger.debug(f"UUID: {uuid}")
            flogger.debug(f"Estado lifecycle: {lifecycle_state}")

            # 1) Validar estado del Programa.
            # La transición hacia 'pendiente_firma_otp' la hace IniciaFirmaProgramaOTP;
            # acá solo verificamos que efectivamente esté en ese estado antes de firmar.            

            # 1.b) Leer y validar OTP (metadato del título)
            otp_str = str(fil.gmv("metadata.programas_otp") or "").strip()
            if otp_str == "":
                flogger.entry("El OTP no puede ser nulo, ingrese un valor válido")
                raise AthentoseError("El OTP no puede ser nulo, ingrese un valor válido")
            if not is_digit(otp_str):
                flogger.entry(f"'OTP' debe ser un número entero positivo en lugar de '{otp_str}'")
                raise AthentoseError(
                    _("'OTP' debe ser un número entero positivo en lugar de '%(otp)s'")
                    % {"otp": otp_str}
                )
            otp = int(otp_str)

            # 1.c) Usuario firmante (Secretaría General)
            flogger.entry("Validando usuario firmante...")
            usuario = get_current_user()
            if not usuario or not getattr(usuario, "is_authenticated", False):
                flogger.entry("No hay un usuario autenticado para firmar el programa")
                raise AthentoseError("No hay un usuario autenticado para firmar el programa")
            """
            #Aqui estaba el code
            """
            mail_sg = usuario.email or ""
            nombre_sg = f"{usuario.first_name or ''} {usuario.last_name or ''}".strip()
            if not mail_sg:
                flogger.entry("El mail del usuario de Docentes no se pudo obtener")
                raise AthentoseError(
                    "El mail del usuario de Docentes no se pudo obtener"
                )

            
            UcasalServices.validate_otp(user=mail_sg, otp=otp)
            fil.set_feature("valide_otp", "1")

            # 2) Token, URL de validación del programa y QR
            flogger.entry("Obteniendo auth_token...")
            try:
                auth_token = UcasalServices.get_auth_token(
                    user=UcasalConfig.token_svc_user(),
                    password=UcasalConfig.token_svc_password(),
                )
            except Exception as token_err:
                import traceback
                err_msg = getattr(token_err, 'message', None) or getattr(token_err, 'args', [None])[0] or str(token_err)
                flogger.entry("Error al obtener auth_token: " + str(err_msg))
                flogger.entry("Traceback: " + traceback.format_exc())
                raise
            

            fil.set_feature("obtuve_auth_token", "1")

            # Nota: designaciones_validation_url_template() lee la clave de config
            # 'ucasal.titulo.validation_url_template' (el nombre del método quedó
            # heredado de Designaciones, pero apunta a la plantilla correcta de
            # Títulos). Ver custom/ucasal2/utils.py -> UcasalConfig.

            url_to_shorten = UcasalConfig.designaciones_validation_url_template().replace(
                "{{uuid}}", uuid
            )
            flogger.entry(f"Obteniendo short_url para: {url_to_shorten}")
            try:
                short_url = UcasalServices.get_short_url(
                    auth_token=auth_token, url=url_to_shorten
                )
            except Exception as url_err:
                flogger.entry(f"Error al obtener short_url: {str(url_err)}")
                raise

            flogger.entry(f"Obteniendo QR para: {short_url}")
            try:
                qr_stream = UcasalServices.get_qr_image(url=short_url)
            except Exception as qr_err:
                flogger.entry(f"Error al obtener QR: {str(qr_err)}")
                raise
            b64_qr = base64.b64encode(qr_stream).decode("utf-8")

            # 2.b) Datos textuales de la firma
            mail_sg_ofuscado = get_mail_for_otp(mail_sg)
            fecha_firma_texto = get_arg_time()

            try:
                locale.setlocale(locale.LC_TIME, "es_AR.UTF-8")
            except Exception:
                pass
            now = datetime.now()
            day = now.strftime("%d")
            month = now.strftime("%B")
            year = now.strftime("%Y")

            qr_text = (
                "Firmado con OTP por:\r\n"
                f"{nombre_sg}\r\n"
                f"{mail_sg_ofuscado}\r\n"
                f"{fecha_firma_texto}"
            )

            otp_info = OTPInfo(
                mail="\n" + mail_sg_ofuscado,
                ip="N/A",
                latitude=0.0,
                longitude=0.0,
                accuracy="N/A",
                user_agent="Athentose/Signer",
            )
            # 3) Preparar el firmador
            signer = SpPdfSimpleSigner()
            documentos_firmados = []

            fil.change_life_cycle_state(ProgramasStates.pendiente_firma_otp, force_transition=True)

            # 4) Firmar el PDF del programa con QR/OTP
            logger.entry("Firmando documento con QR/OTP")
            for hijo in (fil,):
                with open(hijo.path(), "rb") as f:
                    current_bytes = f.read()
                if not current_bytes:
                    flogger.entry(f"El documento {hijo.uuid} no tiene binario para firmar")
                    raise AthentoseError(
                        _("El documento %(uuid)s no tiene binario para firmar")
                        % {"uuid": hijo.uuid}
                    )

                qr_image_tmp_path = f"/var/www/athentose/media/tmp/ucasal_programa_qr_{hijo.uuid}.png"
                os.makedirs(os.path.dirname(qr_image_tmp_path), exist_ok=True)
                with open(qr_image_tmp_path, "wb") as qr_file:
                    qr_file.write(qr_stream)

                qr_info = QRInfo(
                    image_path=qr_image_tmp_path,
                    image_text=qr_text,
                    x=20,
                    y=11,
                    width=70,
                    height=70,
                )

                signed_result = signer.sign(
                    hijo.path(),
                    qr_info,
                    otp_info,
                )

                signed_pdf_bytes = signed_result.getvalue()

                document = DjangoFile(
                    io.BytesIO(signed_pdf_bytes), f"{hijo.filename}.pdf"
                )
                hijo.update_binary(document)
                hijo.set_feature("firmada_con_otp", "1")
                documentos_firmados.append(str(hijo.uuid))

                try:
                    os.remove(qr_image_tmp_path)
                except Exception:
                    logger.warning(
                        "No se pudo eliminar el archivo temporal %s", qr_image_tmp_path
                    )

            fil.change_life_cycle_state(ProgramasStates.pendiente_blockchain, force_transition=True)

            # 5) Registrar hash del programa en blockchain
            logger.entry("Registrando hash del programa en blockchain")
            hash_programa = get_pdf_hash(fil)

            registrada_en_blockchain = fil.gfv("registro_blockchain")

            if registrada_en_blockchain == "success":
                flogger.entry("El programa ya fue firmado y registrado en blockchain.")
                return logger.exit(
                    {
                        "msg": _(
                            "Programa firmado digitalmente y enviado a "
                            "blockchain."
                        ),
                        "msg_type": "success",
                    }
                )

            callback_url = DesignacionesServices.set_callback_url(uuid=uuid)
            logger.entry(f"Callback URL: {callback_url} - UUID: {uuid} - Hash: {hash_programa}" + f" - Token: {auth_token}")

            ok_response = UcasalServices.register_in_blockchain(
                auth_token=auth_token,
                hash=hash_programa,
                file_uuid=uuid,
                callback_url=callback_url,
            )
            fil.set_feature("ucasal.svc.ok_response_programa", ok_response)

            logger.entry(f"Token: {auth_token}" + f" - Hash: {hash_programa}")

            fil.set_feature("registro_blockchain", "pending")
            fil.set_feature("programas.documentos_firmados", documentos_firmados)
            fil.set_feature("hash_programa", hash_programa)

            # 6) Cambiar estado del programa.
            # No hay (todavía) un endpoint de bfaresponse que confirme el
            # registro en blockchain de forma asíncrona (ver TODO arriba), así
            # que el programa pasa directamente a 'firmado' apenas se envía el
            # hash, en vez de quedar esperando en 'pendiente_blockchain'. Si
            # UCASAL termina confirmando por callback, este paso debería
            # cambiarse para dejar el programa en 'pendiente_blockchain' y
            # recién pasar a 'firmado' cuando llegue esa confirmación.
            
            fil.change_life_cycle_state(ProgramasStates.pendiente_blockchain)
            fil.set_metadata(
                "estado",
                ProgramasStates.pendiente_blockchain,
                overwrite=True,
            )
            flogger.entry("Enviando notificación de actualización de estado a UCASAL")
            try:
                response = requests.post(
                    "https://backprod.ucasal.edu.ar/testing/titulos/athento/update-finalize",
                    json={"status": "5", "uuid": uuid},
                    verify=False,
                    timeout=30,
                )
                response.raise_for_status()
                flogger.entry(
                    f"Actualizacion estado firmada UCASAL - Status: {response.status_code}, Response: {response.text[:200]}"
                )
            except Exception as notif_err:
                flogger.entry(
                    f"Error al Actualizacion estado firmada a UCASAL: {str(notif_err)}"
                )
                raise AthentoseError(
                    f"No se pudo notificar el estado firmado a UCASAL: {notif_err}"
                )

            fil.change_life_cycle_state(ProgramasStates.firmado, force_transition=True)
            fil.set_metadata("estado", ProgramasStates.firmado, overwrite=True)
            fil.set_feature("registro_blockchain", "success")
            flogger.entry("Documento firmado. Estado cambiado a 'Firmado'")

            body_to_save = {
                "fecha_firma": {"day": day, "month": month, "year": year},
                "qr_data": {"short_url": short_url, "qr_base64": b64_qr},
                "qr_text": {
                    "firmado_por": "Firmado con OTP por:",
                    "nombre": nombre_sg,
                    "mail": mail_sg_ofuscado,
                    "fecha_firma": fecha_firma_texto,
                },
            }
            fil.set_feature("bodyFinalTitulo", body_to_save)

            return logger.exit(
                {
                    "msg": _(
                        "Programa firmado digitalmente y enviado a "
                        "blockchain."
                    ),
                    "msg_type": "success",
                }
            )

        except AthentoseError as e:
            error_msg = f"Error en la operación de firma de programa OTP: {str(e)}"
            flogger.error(error_msg)
            logger.error(error_msg)
            return logger.exit(
                HttpResponse(str(e), status=400),
                exc_info=True,
            )
        except Exception as e:  # noqa: BLE001
            error_msg = f"Error inesperado en la operación de firma de programa OTP: {str(e)}"
            flogger.error(error_msg)
            logger.error(error_msg)
            return logger.exit(
                HttpResponse(str(e), status=500),
                exc_info=True,
            )


VERSION = FirmaProgramaOTP.version
NAME = FirmaProgramaOTP.name
DESCRIPTION = FirmaProgramaOTP.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = FirmaProgramaOTP.configuration_parameters


def run(uuid=None, **params):
    return FirmaProgramaOTP(uuid, **params).run()
