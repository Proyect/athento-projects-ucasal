import requests
import os

BASE = os.environ.get('API_BASE_URL', 'http://localhost:8012')
url = f"{BASE.rstrip('/')}/athento/files/"

files = {
    'file': ('dummy.txt', b'contenido de prueba', 'text/plain'),
}

data = {
    'filename': '123/10/3/16/2/8707',
    'doctype': 'test',
    'serie': 'serie1',
    'metadatas': '{}',
}

try:
    resp = requests.post(url, files=files, data=data, timeout=20)
    print('STATUS', resp.status_code)
    print('BODY', resp.text[:500])
except Exception as e:
    print('ERROR', type(e).__name__, str(e))
