import os
import sys
import json
import requests

BASE = os.environ.get('API_BASE_URL', 'http://localhost:8013').rstrip('/')
create_url = f"{BASE}/athento/files/"

def main():
    # 1) Crear archivo
    files = {
        'file': ('dummy.txt', b'contenido de prueba', 'text/plain'),
    }
    data = {
        'filename': '123/10/3/16/2/8707',
        'doctype': 'form_titulo',
        'serie': '2320305d-3169-464f-a7ea-76a2c62d79c0',
        'metadatas': json.dumps({'metadata.form_titulo_firmar': 'ok'})
    }
    print('[CREATE] POST', create_url)
    r = requests.post(create_url, files=files, data=data, timeout=60)
    print('[CREATE][STATUS]', r.status_code)
    print('[CREATE][BODY]', r.text[:500])
    r.raise_for_status()
    resp = r.json()
    uuid = resp.get('uuid')
    if not uuid:
        print('[ERROR] No se obtuvo uuid en la creación')
        sys.exit(2)

    # 2) Detail
    detail_url = f"{BASE}/athento/files/{uuid}/detail/"
    print('[DETAIL] GET', detail_url)
    r2 = requests.get(detail_url, timeout=60)
    print('[DETAIL][STATUS]', r2.status_code)
    print('[DETAIL][BODY]', r2.text[:500])
    r2.raise_for_status()

    # 3) Download
    download_url = f"{BASE}/athento/files/{uuid}/download"
    print('[DOWNLOAD] GET', download_url)
    r3 = requests.get(download_url, stream=True, timeout=60)
    print('[DOWNLOAD][STATUS]', r3.status_code)
    chunk = next(r3.iter_content(chunk_size=256), b'')
    print('[DOWNLOAD][FIRST_BYTES]', chunk[:64])
    r3.close()

if __name__ == '__main__':
    main()
