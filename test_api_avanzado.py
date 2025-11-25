#!/usr/bin/env python
"""
Script avanzado para probar endpoints que requieren datos previos
Soporta tanto ambiente local como remoto (UAT/Producción)
"""
import os
import requests
import json
import uuid
import sys
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8012")
ADMIN_USERNAME = os.getenv("API_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("API_ADMIN_PASSWORD", "admin123")
DEFAULT_OTP_CODE = os.getenv("API_TEST_OTP", "123456")

# Detectar si es ambiente remoto para ajustar timeouts
IS_REMOTE = BASE_URL.startswith("https://")
DEFAULT_TIMEOUT = 30 if IS_REMOTE else 5

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_status(status, message):
    if status:
        print(f"[OK] {message}")
    else:
        print(f"[ERROR] {message}")

def get_auth_token():
    """Obtener token JWT"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login/",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=DEFAULT_TIMEOUT
        )
        if response.status_code == 200:
            return response.json().get("access")
        return None
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout al obtener token")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Error de conexión al obtener token")
        return None
    except Exception as e:
        print(f"[ERROR] Error obteniendo token: {e}")
        return None

def crear_acta_via_api(token, titulo, estado="recibida"):
    """Crear acta usando Django shell via subprocess"""
    import subprocess
    script = f"""
from endpoints.actas.models import Acta
import uuid
acta = Acta.objects.create(
    uuid=uuid.uuid4(),
    titulo="{titulo}",
    descripcion="Acta creada para pruebas",
    docente_asignado="profesor@test.com",
    nombre_docente="Prof. Test",
    codigo_sector="001",
    estado="{estado}"
)
print(acta.uuid)
"""
    try:
        result = subprocess.run(
            ["python", "manage.py", "shell", "-c", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            uuid_str = result.stdout.strip().split('\n')[-1]
            return uuid_str
    except Exception as e:
        print(f"[ERROR] Error creando acta: {e}")
    return None

def test_sendotp(acta_uuid):
    """Probar envío de OTP"""
    print_section(f"ENVIAR OTP - Acta {acta_uuid}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/actas/{acta_uuid}/sendotp/",
            timeout=DEFAULT_TIMEOUT * 2
        )
        
        if response.status_code == 200:
            data = response.json()
            print_status(True, f"OTP enviado: {data.get('message', 'OK')}")
            print(f"   Estado actual: {data.get('estado', 'N/A')}")
            return True
        else:
            print_status(False, f"Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
    except Exception as e:
        print_status(False, f"Error: {e}")
        return False

def _parse_otp(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def test_registerotp(acta_uuid, otp_code=None):
    """Probar registro de OTP"""
    print_section(f"REGISTRAR OTP - Acta {acta_uuid}")

    otp_to_use = _parse_otp(otp_code if otp_code is not None else DEFAULT_OTP_CODE)
    
    try:
        response = requests.post(
            f"{BASE_URL}/actas/{acta_uuid}/registerotp/",
            json={
                "otp": otp_to_use,
                "ip": "192.168.1.100",
                "latitude": -34.6037,
                "longitude": -58.3816,
                "accuracy": "10m",
                "user_agent": "Mozilla/5.0 (Test Browser)"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print_status(True, f"OTP registrado: {data.get('message', 'OK')}")
            print(f"   Estado: {data.get('estado', 'N/A')}")
            print(f"   Hash documento: {data.get('hash_documento', 'N/A')[:20]}...")
            return True
        else:
            print_status(False, f"Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:300]}")
            return False
    except Exception as e:
        print_status(False, f"Error: {e}")
        return False

def test_bfaresponse(acta_uuid, status="success"):
    """Probar callback de blockchain"""
    print_section(f"CALLBACK BLOCKCHAIN - Acta {acta_uuid} ({status})")
    
    try:
        response = requests.post(
            f"{BASE_URL}/actas/{acta_uuid}/bfaresponse/",
            json={"status": status},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_status(True, f"Callback procesado: {data.get('message', 'OK')}")
            print(f"   Estado final: {data.get('estado', 'N/A')}")
            return True
        else:
            print_status(False, f"Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
    except Exception as e:
        print_status(False, f"Error: {e}")
        return False

def test_reject(acta_uuid, motivo="Prueba de rechazo"):
    """Probar rechazo de acta"""
    print_section(f"RECHAZAR ACTA - Acta {acta_uuid}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/actas/{acta_uuid}/reject/",
            json={"motivo": motivo},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_status(True, f"Acta rechazada: {data.get('message', 'OK')}")
            print(f"   Estado: {data.get('estado', 'N/A')}")
            return True
        else:
            print_status(False, f"Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
    except Exception as e:
        print_status(False, f"Error: {e}")
        return False

def obtener_actas_existentes():
    """Obtener lista de actas existentes desde Django shell"""
    import subprocess
    import os
    script = """
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from endpoints.actas.models import Acta
actas = Acta.objects.all()[:10]
for acta in actas:
    print(f"{acta.uuid}|{acta.titulo}|{acta.estado}")
"""
    try:
        result = subprocess.run(
            ["python", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            actas = []
            for line in result.stdout.strip().split('\n'):
                if '|' in line and not line.startswith('>>>'):
                    parts = line.split('|')
                    if len(parts) >= 3:
                        actas.append({
                            'uuid': parts[0],
                            'titulo': parts[1],
                            'estado': parts[2]
                        })
            return actas
    except Exception as e:
        print(f"[ERROR] Error obteniendo actas: {e}")
        print(f"[DEBUG] stdout: {result.stdout if 'result' in locals() else 'N/A'}")
        print(f"[DEBUG] stderr: {result.stderr if 'result' in locals() else 'N/A'}")
    return []

def main():
    print("\n" + "PRUEBAS AVANZADAS DEL SISTEMA UCASAL".center(70))
    print("=" * 70)
    
    # Verificar servidor
    try:
        requests.get(f"{BASE_URL}/", timeout=2)
        print("[OK] Servidor disponible")
    except:
        print("[ERROR] Servidor no disponible en http://localhost:8012")
        return
    
    # Obtener token
    token = get_auth_token()
    if not token:
        print("[WARN] No se pudo obtener token, algunas pruebas pueden fallar")
    else:
        print("[OK] Token JWT obtenido")
    
    # Obtener actas existentes
    print_section("OBTENIENDO ACTAS EXISTENTES")
    actas = obtener_actas_existentes()
    
    if not actas:
        print("[INFO] No hay actas existentes. Creando actas de prueba...")
        print("[INFO] Ejecuta: python manage.py shell")
        print("[INFO] Luego ejecuta:")
        print("""
from endpoints.actas.models import Acta
import uuid

acta1 = Acta.objects.create(
    uuid=uuid.uuid4(),
    titulo="Acta de Prueba - Recibida",
    descripcion="Para probar envío de OTP",
    docente_asignado="profesor@test.com",
    nombre_docente="Prof. Test",
    codigo_sector="001",
    estado="recibida"
)

acta2 = Acta.objects.create(
    uuid=uuid.uuid4(),
    titulo="Acta de Prueba - Pendiente OTP",
    descripcion="Para probar registro de OTP",
    docente_asignado="profesor2@test.com",
    nombre_docente="Prof. Test 2",
    codigo_sector="002",
    estado="pendiente_otp"
)

acta3 = Acta.objects.create(
    uuid=uuid.uuid4(),
    titulo="Acta de Prueba - Pendiente OTP (para rechazar)",
    descripcion="Para probar rechazo",
    docente_asignado="profesor3@test.com",
    nombre_docente="Prof. Test 3",
    codigo_sector="003",
    estado="pendiente_otp"
)

print(f"Actas creadas:")
print(f"  - {acta1.uuid} ({acta1.estado})")
print(f"  - {acta2.uuid} ({acta2.estado})")
print(f"  - {acta3.uuid} ({acta3.estado})")
        """)
        return
    
    print(f"[OK] Se encontraron {len(actas)} actas")
    for i, acta in enumerate(actas, 1):
        print(f"   {i}. {acta['titulo']} ({acta['estado']}) - {acta['uuid']}")
    
    # Probar endpoints con las actas
    resultados = []
    
    # Buscar acta en estado "recibida" para enviar OTP
    acta_recibida = next((a for a in actas if a['estado'] == 'recibida'), None)
    if acta_recibida:
        resultados.append(("sendotp", test_sendotp(acta_recibida['uuid'])))
    
    # Buscar acta en estado "pendiente_otp" para registrar OTP
    acta_pendiente = next((a for a in actas if a['estado'] == 'pendiente_otp'), None)
    if acta_pendiente:
        # Nota: El OTP real vendría del email, usamos uno mock
        print("[INFO] Nota: Usando OTP mock (123456). En producción, usar OTP real del email.")
        resultados.append(("registerotp", test_registerotp(acta_pendiente['uuid'], 123456)))
    
    # Buscar acta en estado "pendiente_blockchain" para callback
    acta_blockchain = next((a for a in actas if a['estado'] == 'pendiente_blockchain'), None)
    if acta_blockchain:
        resultados.append(("bfaresponse", test_bfaresponse(acta_blockchain['uuid'], "success")))
    
    # Buscar otra acta en "pendiente_otp" para rechazar
    actas_pendientes = [a for a in actas if a['estado'] == 'pendiente_otp']
    if len(actas_pendientes) > 1:
        resultados.append(("reject", test_reject(actas_pendientes[1]['uuid'])))
    
    # Resumen
    print_section("RESUMEN DE PRUEBAS")
    exitosos = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    print(f"Pruebas ejecutadas: {total}")
    print(f"Pruebas exitosas: {exitosos}")
    print(f"Pruebas fallidas: {total - exitosos}")
    
    if exitosos == total and total > 0:
        print("\n[OK] ¡Todas las pruebas pasaron!")
    elif total > 0:
        print("\n[WARN] Algunas pruebas fallaron. Revisa los detalles arriba.")
    else:
        print("\n[INFO] No se pudieron ejecutar pruebas. Crea actas desde el admin primero.")
    
    print("\n[INFO] Para crear más actas de prueba:")
    print("       1. Ve a: http://localhost:8012/admin/actas/acta/")
    print("       2. O usa Django shell: python manage.py shell")

if __name__ == "__main__":
    main()

