# -*- coding: utf-8 -*-
# Operation properties
from operations.classes.document_operation import DocumentOperation
from custom.sp_libs.python.logging import SpLogger, SpFeatureLogger, NullSpFeatureLogger
from django.utils.translation import gettext as _
from django.http import HttpResponse

from core.exceptions import AthentoseError
from file.models import File
from django.core.files import File as DjangoFile
from django_currentuser.middleware import get_current_user

from custom.ucasal2.utils import TituloStates
from custom.ucasal2.external_services.ucasal.ucasal_services import UcasalServices
from custom.ucasal2.external_services.ucasal.designaciones_services import DesignacionesServices
from custom.ucasal2.utils import UcasalConfig
from custom.ucasal2.utils import is_digit, get_mail_for_otp, get_arg_time, get_pdf_hash
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

from file.foperations import op_send_by_email

class FirmaTituloOTP(DocumentOperation):
    """Firma analítico y diploma de un título con OTP y QR, y los registra en blockchain.

    Flujo esperado:
      - El documento padre (título) debe estar en estado TituloStates.pendiente_firma_otp
      - El OTP se ingresa en un metadato del título (metadata.titulo_otp)
      - Se firman los PDFs hijos (analítico y diploma) usando el mismo QR/OTP
      - Se registran ambos hashes en blockchain
      - El título pasa a estado TituloStates.pendiente_blockchain
    """

    version = "1.0"
    name = _("FirmaTituloOTP")
    description = _(
        "Firma analítico y diploma de un título con OTP y QR, y los registra en blockchain  pruebas"
    )
    configuration_parameters = {}
    _logger: SpLogger = SpLogger("athentose", "FirmaTituloOTP")

    def execute(self, *args, **kwargs):  # noqa: D401
        flogger: SpFeatureLogger = NullSpFeatureLogger()
        logger = self._logger
        logger.entry()

        fil_padre = self.document
        uuid_padre = str(fil_padre.uuid)
        lifecycle_state = fil_padre.life_cycle_state.name if fil_padre.life_cycle_state else ""
        estado_meta = fil_padre.gfv("estado") or lifecycle_state

        try:
            flogger = SpFeatureLogger.getLogger(fil_padre)

            if estado_meta == "Pendiente  de validacion FSG (secretaria general)":
                nuevo_estado = "Pendiente de Firma OTP"
                fil_padre.set_metadata("estado", nuevo_estado, overwrite=True)
                fil_padre.change_life_cycle_state(nuevo_estado)

                op_send_by_email.run(
                    uuid_padre,
                    notifications_template='titulos_notificacion_pendiente_firma',
                    send_to_groups='SECRETARIA GRAL',
                    area='TITULOS'
                ) 

                return logger.exit(
                    {
                        "msg": f"El título {uuid_padre} avanzó a '{nuevo_estado}'",
                        "msg_type": "success",
                    }
                )
            """            
            # 1) Validar estado del título padre
            
            lifecycle_state = fil_padre.life_cycle_state.name if fil_padre.life_cycle_state else ""
            if lifecycle_state != TituloStates.pendiente_firma_otp:
                flogger.entry(
                    f"Sólo se puede firmar el título si está en estado '{TituloStates.pendiente_firma_otp}', "
                    f"pero el estado actual es '{lifecycle_state or ''}'."
                )
                raise AthentoseError(
                    _(
                        "Sólo se puede firmar el título si está en estado '%(esperado)s', "
                        "pero el estado actual es '%(actual)s'."
                    )
                    % {
                        "esperado": TituloStates.pendiente_firma_otp,
                        "actual": lifecycle_state or "",
                    }
                ) """

            # 1.b) Leer y validar OTP (metadato del título)
            otp_str = str(fil_padre.gmv("metadata.titulo_otp") or "").strip()
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
            usuario = get_current_user()
            if not usuario or not getattr(usuario, "is_authenticated", False):
                flogger.entry("No hay un usuario autenticado para firmar el título")
                raise AthentoseError("No hay un usuario autenticado para firmar el título")

            if not usuario.groups.filter(name="SECRETARIA GRAL").exists():
                flogger.entry("El usuario logueado no pertenece al grupo 'Secretaría General'")
                raise AthentoseError(
                    "El usuario logueado no pertenece al grupo 'Secretaría General'"
                )

            mail_sg = usuario.email or ""
            nombre_sg = f"{usuario.first_name or ''} {usuario.last_name or ''}".strip()
            if not mail_sg:
                flogger.entry("El mail del usuario de Secretaría General no se pudo obtener")
                raise AthentoseError(
                    "El mail del usuario de Secretaría General no se pudo obtener"
                )

            # 1.d) Validar OTP contra servicio UCASAL
            UcasalServices.validate_otp(user=mail_sg, otp=otp)
            fil_padre.set_feature("valide_otp", "1")

            # 2) Token, URL de validación del título y QR
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
            fil_padre.set_feature("obtuve_auth_token", "1")

            url_to_shorten = UcasalConfig.designaciones_validation_url_template().replace(
                "{{uuid}}", uuid_padre
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

            # 3) Encontrar hijos del folder (analítico y diploma)
            flogger.entry(f"Buscando expediente titulo y analitico")
            hijos = fil_padre.get_children()
            flogger.entry(f"Hijos encontrados: {len(hijos)}")
            hijo_analitico = None
            hijo_diploma = None

            for hijo in hijos:
                # TODO: ajusta estos criterios a tus doctypes/metadata reales
                if hijo.doctype.name == "analitico":
                    hijo_analitico = hijo
                elif hijo.doctype.name == "titulo":
                    hijo_diploma = hijo

            if not hijo_analitico or not hijo_diploma:
                flogger.entry(
                    "No se encontraron ambos documentos (Analítico y Diploma) relacionados "
                    "al título para firmar."
                )
                raise AthentoseError(
                    _(
                        "No se encontraron ambos documentos (Analítico y Diploma) relacionados "
                        "al título para firmar."
                    )
                )

            signer = SpPdfSimpleSigner()
            documentos_firmados = []

            # 4) Firmar ambos PDFs con el mismo QR/OTP
            for hijo in (hijo_analitico, hijo_diploma):
                with open(hijo.path(), "rb") as f:
                    current_bytes = f.read()
                if not current_bytes:
                    flogger.entry(f"El documento {hijo.uuid} no tiene binario para firmar")
                    raise AthentoseError(
                        _("El documento %(uuid)s no tiene binario para firmar")
                        % {"uuid": hijo.uuid}
                    )

                qr_image_tmp_path = f"/var/www/athentose/media/tmp/ucasal_titulo_qr_{hijo.uuid}.png"
                os.makedirs(os.path.dirname(qr_image_tmp_path), exist_ok=True)
                with open(qr_image_tmp_path, "wb") as qr_file:
                    qr_file.write(qr_stream)

                qr_info = QRInfo(
                    image_path=qr_image_tmp_path,
                    image_text=qr_text,
                    x=845,
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

            # 5) Registrar hashes de analítico y diploma en blockchain
            registrada_en_blockchain = fil_padre.gfv("registro_blockchain")
            if registrada_en_blockchain == "pending":
                flogger.entry(
                    "El título ya había sido enviado a blockchain y su resultado aún "
                    "está pendiente."
                )
                raise AthentoseError(
                    _(
                        "El título ya había sido enviado a blockchain y su resultado aún "
                        "está pendiente."
                    )
                )
            if registrada_en_blockchain == "success":
                flogger.entry("El título ya está registrado en blockchain.")
                raise AthentoseError(_("El título ya está registrado en blockchain."))

            hash_analitico = get_pdf_hash(hijo_analitico)
            # TODO: ajusta si tienes una plantilla específica de callback para títulos
            callback_url = DesignacionesServices.set_callback_url(uuid=uuid_padre)   # placeholder genérico

            ok_response_analitico = UcasalServices.register_in_blockchain(
                auth_token=auth_token,
                hash=hash_analitico,
                file_uuid=str(hijo_analitico.uuid),
                callback_url=callback_url,
            )
            hijo_analitico.set_feature(
                "ucasal.svc.ok_response_analitico", ok_response_analitico
            )

            hash_diploma = get_pdf_hash(hijo_diploma)
            ok_response_diploma = UcasalServices.register_in_blockchain(
                auth_token=auth_token,
                hash=hash_diploma,
                file_uuid=str(hijo_diploma.uuid),
                callback_url=callback_url,
            )
            hijo_diploma.set_feature("ucasal.svc.ok_response_diploma", ok_response_diploma)

            fil_padre.set_feature("registro_blockchain", "pending")
            fil_padre.set_feature("titulos.documentos_firmados", documentos_firmados)

            # 6) Cambiar estado del padre a pendiente_blockchain
            if fil_padre.life_cycle_state.name == TituloStates.pendiente_firma_otp:
                fil_padre.change_life_cycle_state(TituloStates.pendiente_blockchain)
                fil_padre.set_metadata(
                    "metadata.lifecycle_state",
                    TituloStates.pendiente_blockchain,
                    overwrite=True,
                )

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
            fil_padre.set_feature("bodyFinalTitulo", body_to_save)

            return logger.exit(
                {
                    "msg": _(
                        "Título firmado digitalmente (analítico y diploma) y enviado a "
                        "blockchain (pendiente de respuesta)."
                    ),
                    "msg_type": "success",
                }
            )

        except AthentoseError as e:
            error_msg = f"Error en la operación de firma de título OTP: {str(e)}"
            flogger.error(error_msg)
            logger.error(error_msg)
            return logger.exit(
                HttpResponse(str(e), status=400),
                exc_info=True,
            )
        except Exception as e:  # noqa: BLE001
            error_msg = f"Error inesperado en la operación de firma de título OTP: {str(e)}"
            flogger.error(error_msg)
            logger.error(error_msg)
            return logger.exit(
                HttpResponse(str(e), status=500),
                exc_info=True,
            )


VERSION = FirmaTituloOTP.version
NAME = FirmaTituloOTP.name
DESCRIPTION = FirmaTituloOTP.description
ORDER = 100
CATEGORY = ""
POSTLOAD = False
POSTCHARACT = False
POSTCLASSIF = False
POSTEXTRACTION = False
CONFIGURATION_PARAMETERS = FirmaTituloOTP.configuration_parameters


def run(uuid=None, **params):
    return FirmaTituloOTP(uuid, **params).run()
