from model import File
import io
import requests
import os
from core.exceptions import AthentoseError
from ucasal.mocks.sp_logger import SpLogger
from base64 import b64encode
from ucasal.utils import UcasalConfig
from model.exceptions.invalid_otp_error import InvalidOtpError
from django.core.cache import cache
import hashlib

class UcasalServices:
    logger = SpLogger("athentose", "UcasalServices")

    #TODO: setear "VERIFY_CERTIFICATE = True" cuando quede productivo 
    VERIFY_CERTIFICATE = False

    # Habilitar mocks locales si UCASAL_USE_MOCKS=true en entorno
    USE_MOCKS = os.environ.get('UCASAL_USE_MOCKS', 'false').lower() == 'true'
    
    # Tiempo de cache para tokens (50 minutos, tokens duran 1 hora)
    TOKEN_CACHE_TIMEOUT = 3000  # 50 minutos en segundos
    
    @classmethod
    def get_auth_token(cls, user:str, password:str)->str:
        """
        Obtiene token de autenticación de UCASAL.
        Usa cache para evitar llamadas repetidas.
        """
        logger = cls.logger
        logger.entry()

        # Modo mock: devolver token estático
        if cls.USE_MOCKS:
            return logger.exit('mock-token')
        
        # Generar clave de cache basada en usuario
        cache_key = f'ucasal_auth_token_{hashlib.md5(user.encode()).hexdigest()}'
        
        # Intentar obtener del cache
        try:
            cached_token = cache.get(cache_key)
            if cached_token:
                logger.debug(f"Token obtenido del cache para usuario {user}")
                return logger.exit(cached_token)
        except Exception as e:
            logger.debug(f"Error accediendo al cache: {e}")
        
        # Si no está en cache, obtener del servicio
        endpoint = UcasalConfig.token_svc_url()
        data = f'usuario={user}&clave={password}'
        
        headers ={'Content-Type': 'application/x-www-form-urlencoded'}  
        logger.debug("Llamando a requests.post con estos parámetros: %s" % str({'url':endpoint, 'data': data, 'headers':headers}))

        response = requests.post(url=endpoint, data=data, headers=headers)

        if response.status_code == requests.codes.ok:
            token = response.text.strip()
            
            # Guardar en cache
            try:
                cache.set(cache_key, token, cls.TOKEN_CACHE_TIMEOUT)
                logger.debug(f"Token guardado en cache para usuario {user}")
            except Exception as e:
                logger.debug(f"Error guardando token en cache: {e}")
            
            return logger.exit(token)
        else:
            raise logger.exit(AthentoseError('Error inesperado obteniento token de autenticación: ' + response.reason), exc_info=True)  
            
    @classmethod
    def get_qr_image(cls, url:str)->bytes:
        """
        Genera imagen QR para una URL.
        Usa cache para URLs ya generadas.
        """
        logger = cls.logger
        logger.entry()
        
        # Generar clave de cache basada en la URL
        cache_key = f'ucasal_qr_image_{hashlib.md5(url.encode()).hexdigest()}'
        
        # Intentar obtener del cache
        try:
            cached_qr = cache.get(cache_key)
            if cached_qr:
                logger.debug(f"QR obtenido del cache para {url[:50]}...")
                return logger.exit(cached_qr)
        except Exception as e:
            logger.debug(f"Error accediendo al cache: {e}")
        
        # Si no está en cache, generar QR
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            qr_bytes = img_bytes.getvalue()
            
            # Guardar en cache (24 horas)
            try:
                cache.set(cache_key, qr_bytes, 86400)
                logger.debug(f"QR guardado en cache")
            except Exception as e:
                logger.debug(f"Error guardando QR en cache: {e}")
            
            return logger.exit(qr_bytes)
        except ImportError:
            # Si no está instalado qrcode, devolver una imagen simple
            logger.debug("qrcode no instalado, devolviendo imagen mock")
            return logger.exit(b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")   
    
    @classmethod
    def get_short_url(cls, auth_token:str, url:str)->str:
        """
        Acorta una URL usando el servicio UCASAL.
        Usa cache para URLs ya acortadas.
        """
        logger = cls.logger
        logger.entry()
        
        # Modo mock: devolver URL local determinística
        if cls.USE_MOCKS:
            return logger.exit(f"http://short.local/{hashlib.md5(url.encode()).hexdigest()[:8]}")
        
        # Generar clave de cache basada en la URL original
        cache_key = f'ucasal_short_url_{hashlib.md5(url.encode()).hexdigest()}'
        
        # Intentar obtener del cache
        try:
            cached_short_url = cache.get(cache_key)
            if cached_short_url:
                logger.debug(f"URL corta obtenida del cache para {url[:50]}...")
                return logger.exit(cached_short_url)
        except Exception as e:
            logger.debug(f"Error accediendo al cache: {e}")
        
        # Si no está en cache, obtener del servicio
        endpoint = UcasalConfig.shorten_url_svc_url()
        headers = {'Authorization': f'Bearer {auth_token}'}
        json = {
          'url': url,
          'entorno': UcasalConfig.shorten_url_svc_env() if UcasalConfig.shorten_url_svc_env() else 'produccion'
        }

        logger.debug("Llamando a requests.post con estos parámetros: %s" % str({'url':endpoint, 'json': json, 'headers':headers}))
        response = requests.post(url=endpoint, headers=headers, json=json, verify=cls.VERIFY_CERTIFICATE)

        logger.debug(f'response.status_code: {response.status_code}')
        logger.debug(f'response.status_code type: { type(response.status_code)}')
        logger.debug(f'requests.codes.ok: {requests.codes.ok}')
        logger.debug(f'requests.codes.ok type: {type(requests.codes.ok)}')
        logger.debug(f'response.text: {response.text}')
        logger.debug(f'response.json(): {response.json()}')

        if response.status_code in [200, 201]:
            short_url = response.json()['url_corta']
            
            # Guardar en cache (24 horas)
            try:
                cache.set(cache_key, short_url, 86400)
                logger.debug(f"URL corta guardada en cache")
            except Exception as e:
                logger.debug(f"Error guardando URL corta en cache: {e}")
            
            return logger.exit(short_url)
        else:
            raise logger.exit(AthentoseError('Error inesperado obteniendo url corta: ' + response.reason), exc_info=True)   


    @classmethod
    def register_in_blockchain(cls, auth_token:str, hash:str, file_uuid:str, callback_url:str)->str:
        #import logging
        #nlogger = logging.getLogger("athentose")

        #nlogger.debug("nlogger - Enter register_in_blockchain")


        logger = cls.logger
        logger.entry()
        #TODO: validar parámetros
                
        endpoint = UcasalConfig.stamps_svc_url()
        headers = {'Authorization': f'Bearer {auth_token}'}
        #TODO: y el file_uuid, no se envía?
        data = {
            'fileHash': hash,
            'callbackUrl': callback_url
        }


        request_info = str({'url':endpoint, 'json':data, 'headers':headers})
        
        logger.debug(f"Llamando a requests.post con estos parametros: {request_info}")
        logger.debug(f"Llamando a requests.post con estos parámetros: {request_info}")

        response = requests.post(url=endpoint, json=data, headers=headers)

        rta = str(response.text)
        logger.debug(f"Respuesta del servicio: {rta}")

        if response.status_code == requests.codes.ok:
            return logger.exit(response.text)
            #TODO: Manejar response?
        else:
            raise logger.exit(AthentoseError('Error inesperado registrando el hash en UCASAL/BFA: ' + response.reason), exc_info=True) 

    @classmethod
    def notify_rejection(cls, auth_token:str, uuid:str, previous_uuid:str, reason:str)->str:
        logger = cls.logger
        logger.entry()
        endpoint = f'{UcasalConfig.change_acta_svc_url()}/{uuid}'
        headers = {'Authorization': f'Bearer {auth_token}'}
        data = {'estado': 1, 'motivo': reason, 'previous_uuid': previous_uuid}
        
        logger.debug("Llamando a requests.patch con estos parámetros: %s" % str({'url':endpoint, 'headers':headers,  'json':data}))
        response = requests.patch(url=endpoint, headers=headers, json=data)

        if response.status_code == requests.codes.ok:
            return logger.exit(response.text)
        else:
            raise logger.exit(AthentoseError('Error inesperado notificando rechazo del acta: ' + response.reason), exc_info=True)   

    @classmethod
    def notify_blockchain_success(cls, auth_token:str, uuid:str)->str:
        logger = cls.logger
        logger.entry()
        endpoint = f'{UcasalConfig.change_acta_svc_url()}/{uuid}'
        headers = {'Authorization': f'Bearer {auth_token}'}
        data = {'estado': 5}
        
        logger.debug("Llamando a requests.patch con estos parámetros: %s" % str({'url':endpoint, 'headers':headers,  'json':data}))
        response = requests.patch(url=endpoint, headers=headers, json={'estado': 5})

        if response.status_code == requests.codes.ok:
            return logger.exit(response.text)
        else:
            raise logger.exit(AthentoseError('Error inesperado notificando éxito registrando el acta en blockchain: ' + response.reason), exc_info=True)   
    
    @classmethod
    def notify_titulo_estado(cls, auth_token: str, uuid: str, estado: int, observaciones: str = '') -> str:
        """
        Notifica a UCASAL el cambio de estado de un Título.
        Si USE_MOCKS=True, simula respuesta exitosa.
        """
        logger = cls.logger
        logger.entry()

        # Modo mock: simular OK
        if cls.USE_MOCKS:
            return logger.exit('OK (mock)')

        endpoint = f'{UcasalConfig.change_acta_svc_url()}/{uuid}'
        headers = {'Authorization': f'Bearer {auth_token}'}
        data = {'estado': estado}
        if observaciones:
            data['observaciones'] = observaciones

        logger.debug("Llamando a requests.patch con estos parámetros: %s" % str({'url': endpoint, 'headers': headers, 'json': data}))
        response = requests.patch(url=endpoint, headers=headers, json=data)

        if response.status_code == requests.codes.ok:
            return logger.exit(response.text)
        else:
            raise logger.exit(AthentoseError('Error inesperado notificando estado de título: ' + response.reason), exc_info=True)
    
    @classmethod
    def validate_otp(cls, user:str, otp:int):
        logger = cls.logger
        logger.entry()

        # Modo mock: aceptar OTP 123456, rechazar otros
        if cls.USE_MOCKS:
            if int(otp) == 123456:
                return logger.exit() # OK
            raise logger.exit(InvalidOtpError('El código OTP es inválido o ha expirado.'))

        endpoint = UcasalConfig.otp_validation_url_template().format(usuario=user, token=otp)
        headers = {}
        
        logger.debug("Llamando a requests.get con estos parámetros: %s" % str({'url':endpoint, 'headers':headers}))
        response = requests.get(url=endpoint, headers=headers)

        if response.status_code == requests.codes.ok:
            return logger.exit() #OK
        if response.status_code == requests.codes.unauthorized:
            raise logger.exit(InvalidOtpError('El código OTP es inválido o ha expirado.'))
        else:
            raise logger.exit(AthentoseError(f'Error inesperado validadando el código OTP: HTTP code: {response.status_code}. HTTP body {response.text}'), exc_info=True)

    # -------------------------
    # Athento Files API helpers
    # -------------------------
    @staticmethod
    def _athento_conf():
        base = (os.environ.get('ATHENTO_BASE_URL') or os.environ.get('API_BASE_URL', 'https://ucasal-uat.athento.com')).rstrip('/')
        user = os.environ.get('ATHENTO_API_USER') or os.environ.get('API_ADMIN_USERNAME')
        pwd = os.environ.get('ATHENTO_API_PASSWORD') or os.environ.get('API_ADMIN_PASSWORD')
        timeout = int(os.environ.get('ATHENTO_TIMEOUT') or os.environ.get('ATHENTO_TIMEOUT_SECONDS') or '60')
        retries = int(os.environ.get('ATHENTO_RETRIES') or '2')
        if not user or not pwd:
            raise AthentoseError('Faltan credenciales de Athento: configure ATHENTO_API_USER/PASSWORD o API_ADMIN_USERNAME/PASSWORD')
        token = b64encode(f"{user}:{pwd}".encode()).decode('utf-8')
        headers = {
            'Authorization': f'Basic {token}'
        }
        return base, headers, timeout, retries

    @classmethod
    def create_file(cls, file_tuple, data: dict):
        logger = cls.logger
        logger.entry()
        base, headers, timeout, retries = cls._athento_conf()
        url = f"{base}/api/v1/file/"
        files = {
            'file': (file_tuple[0], file_tuple[1], file_tuple[2])
        }
        form = {
            'filename': data.get('filename'),
            'doctype': data.get('doctype'),
            'serie': data.get('serie')
        }
        metadatas = data.get('metadatas') or {}
        for k, v in metadatas.items():
            form[k] = str(v)
        last_exc = None
        for _ in range(retries + 1):
            try:
                resp = requests.post(url, files=files, data=form, headers=headers, timeout=timeout, verify=cls.VERIFY_CERTIFICATE)
                if resp.status_code in (200, 201):
                    try:
                        j = resp.json()
                    except Exception:
                        j = {'result': resp.text}
                    return logger.exit({
                        'success': True,
                        'uuid': j.get('uuid') or j.get('id') or j.get('result', {}).get('uuid'),
                        'filename': form['filename'],
                        'doctype': form['doctype'],
                        'serie': form['serie']
                    })
                raise AthentoseError(f"Athento create error: HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                last_exc = e
        raise logger.exit(last_exc)

    @classmethod
    def update_file(cls, uuid: str, file_tuple=None, data: dict | None = None):
        logger = cls.logger
        logger.entry()
        base, headers, timeout, retries = cls._athento_conf()
        url = f"{base}/api/v1/file/{uuid}/"
        files = None
        if file_tuple:
            files = {'file': (file_tuple[0], file_tuple[1], file_tuple[2])}
        form = {}
        if data:
            if data.get('filename'):
                form['filename'] = data.get('filename')
            metadatas = data.get('metadatas') or {}
            for k, v in metadatas.items():
                form[k] = str(v)
        last_exc = None
        for _ in range(retries + 1):
            try:
                resp = requests.put(url, files=files, data=form, headers=headers, timeout=timeout, verify=cls.VERIFY_CERTIFICATE)
                if resp.status_code in (200, 201):
                    return logger.exit({'success': True, 'uuid': uuid, 'updated': list(form.keys()) + (['file'] if files else [])})
                raise AthentoseError(f"Athento update error: HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                last_exc = e
        raise logger.exit(last_exc)

    @classmethod
    def delete_file(cls, uuid: str):
        logger = cls.logger
        logger.entry()
        base, headers, timeout, retries = cls._athento_conf()
        url = f"{base}/api/v1/file/{uuid}/"
        last_exc = None
        for _ in range(retries + 1):
            try:
                resp = requests.delete(url, headers=headers, timeout=timeout, verify=cls.VERIFY_CERTIFICATE)
                if resp.status_code in (200, 202, 204):
                    return logger.exit(None)
                raise AthentoseError(f"Athento delete error: HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                last_exc = e
        raise logger.exit(last_exc)

    @classmethod
    def get_file(cls, uuid: str, fetch_mode: str | None = None):
        logger = cls.logger
        logger.entry()
        base, headers, timeout, retries = cls._athento_conf()
        # Según uso actual, Athento acepta POST con form 'X-Fetch-Mode'
        url = f"{base}/api/v1/file/{uuid}"
        form = {}
        if fetch_mode:
            form['X-Fetch-Mode'] = fetch_mode
        last_exc = None
        for _ in range(retries + 1):
            try:
                resp = requests.post(url, data=form, headers=headers, timeout=timeout, verify=cls.VERIFY_CERTIFICATE)
                if resp.status_code in (200, 201):
                    try:
                        return logger.exit(resp.json())
                    except Exception:
                        return logger.exit({'raw': resp.text})
                raise AthentoseError(f"Athento get error: HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                last_exc = e
        raise logger.exit(last_exc)

    @classmethod
    def download_file(cls, uuid: str):
        logger = cls.logger
        logger.entry()
        base, headers, timeout, retries = cls._athento_conf()
        url = f"{base}/api/v1/file/{uuid}/download"
        last_exc = None
        for _ in range(retries + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=timeout, stream=True, verify=cls.VERIFY_CERTIFICATE)
                if resp.status_code == 200:
                    filename = None
                    cd = resp.headers.get('Content-Disposition')
                    if cd and 'filename=' in cd:
                        filename = cd.split('filename=')[-1].strip('"')
                    content_type = resp.headers.get('Content-Type', 'application/octet-stream')
                    return logger.exit((resp.iter_content(chunk_size=8192), filename, content_type))
                raise AthentoseError(f"Athento download error: HTTP {resp.status_code}")
            except Exception as e:
                last_exc = e
        raise logger.exit(last_exc)

    @classmethod
    def search_query(cls, sql: str, page: int = 1, page_size: int = 20):
        logger = cls.logger
        logger.entry()
        base, headers, timeout, retries = cls._athento_conf()
        url = f"{base}/api/v1/search/query/?page={page}&page_size={page_size}"
        payload = { 'query': sql }
        last_exc = None
        for _ in range(retries + 1):
            try:
                resp = requests.post(url, headers={**headers, 'Content-Type': 'application/json'}, json=payload, timeout=timeout, verify=cls.VERIFY_CERTIFICATE)
                if resp.status_code in (200, 201):
                    return logger.exit(resp.json())
                raise AthentoseError(f"Athento search query error: HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                last_exc = e
        raise logger.exit(last_exc)

    @classmethod
    def search_resultset(cls, sql: str, page: int = 1, page_size: int = 20):
        logger = cls.logger
        logger.entry()
        base, headers, timeout, retries = cls._athento_conf()
        url = f"{base}/api/v1/search/resultset/?page={page}&page_size={page_size}"
        payload = { 'query': sql }
        last_exc = None
        for _ in range(retries + 1):
            try:
                resp = requests.post(url, headers={**headers, 'Content-Type': 'application/json'}, json=payload, timeout=timeout, verify=cls.VERIFY_CERTIFICATE)
                if resp.status_code in (200, 201):
                    return logger.exit(resp.json())
                raise AthentoseError(f"Athento search resultset error: HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                last_exc = e
        raise logger.exit(last_exc)