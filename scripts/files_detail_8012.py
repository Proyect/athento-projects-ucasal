import requests
BASE='http://localhost:8012'
UUID='aab8bd6e-761d-4c0b-9bce-439e2333b25a'
url=f"{BASE}/athento/files/{UUID}/detail/"
print('GET', url)
r=requests.get(url, timeout=30)
print('STATUS', r.status_code)
print('BODY', r.text)
