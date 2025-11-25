#!/usr/bin/env python
"""
Script completo para probar endpoints de títulos
Soporta tanto ambiente local como remoto (UAT/Producción)
"""
import requests
import json
import uuid
import sys
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8012")
ADMIN_USERNAME = os.getenv("API_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("API_ADMIN_PASSWORD", "admin123")
DEFAULT_OTP_CODE = os.getenv("API_TEST_OTP", "123456")
DEFAULT_OTP_USER = os.getenv("API_TEST_OTP_USER", "test@ucasal.edu.ar")

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

def _parse_otp(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value

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

def obtener_titulos_existentes():
    """Obtener lista de títulos existentes desde Django"""
    import subprocess
    script = """
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from model.File import File
from ucasal.utils import titulo_doctype_name

titulos = File.objects.filter(doctype_obj__name=titulo_doctype_name)[:10]
for titulo in titulos:
    print(f"{titulo.uuid}|{titulo.titulo}|{titulo.life_cycle_state.name}")
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
            titulos = []
            for line in result.stdout.strip().split('\n'):
                if '|' in line and not line.startswith('>>>'):
                    parts = line.split('|')
                    if len(parts) >= 3:
                        titulos.append({
                            'uuid': parts[0],
                            'titulo': parts[1],
                            'estado': parts[2]
                        })
            return titulos
    except Exception as e:
        print(f"[ERROR] Error obteniendo títulos: {e}")
    return []

def test_qr():
    """Probar generación de QR para títulos"""
    print_section("GENERAR QR PARA TÍTULO")
    
    try:
        response = requests.post(
            f"{BASE_URL}/titulos/qr/",
            json={"url": "https://www.ucasal.edu.ar/validar/titulo/test-uuid"},
            timeout=10
        )
        
        if response.status_code == 200:
            print_status(True, f"QR generado: {len(response.content)} bytes")
            # Guardar imagen si es posible
            try:
                with open("qr_titulo_test.png", "wb") as f:
                    f.write(response.content)
                print("[OK] Imagen guardada en qr_titulo_test.png")
            except:
                print("[INFO] No se pudo guardar imagen")
            return True
        else:
            print_status(False, f"Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
    except Exception as e:
        print_status(False, f"Error: {e}")
        return False

def test_informar_estado(titulo_uuid, estado="Aprobado por UA"):
    """Probar informar cambio de estado"""
    print_section(f"INFORMAR ESTADO - Título {titulo_uuid}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/titulos/{titulo_uuid}/estado/",
            json={
                "estado": estado,
                "observaciones": "Título aprobado correctamente para pruebas"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print_status(True, f"Estado informado: {data.get('estado', 'OK')}")
            print(f"   Estado código UCASAL: {data.get('estado_codigo', 'N/A')}")
            return True
        else:
            print_status(False, f"Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:300]}")
            return False
    except Exception as e:
        print_status(False, f"Error: {e}")
        return False

def test_validar_otp(titulo_uuid, otp_code=None, usuario=None):
    """Probar validación de OTP"""
    print_section(f"VALIDAR OTP - Título {titulo_uuid}")

    otp_to_use = _parse_otp(otp_code if otp_code is not None else DEFAULT_OTP_CODE)
    user_to_use = usuario or DEFAULT_OTP_USER

    try:
        response = requests.post(
            f"{BASE_URL}/titulos/{titulo_uuid}/validar-otp/",
            json={
                "otp": otp_to_use,
                "usuario": user_to_use
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_status(True, f"OTP validado: {data.get('otp_valido', False)}")
            print(f"   Usuario: {data.get('usuario', 'N/A')}")
            return True
        else:
            print_status(False, f"Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:300]}")
            print("[INFO] Nota: El OTP debe ser válido del servicio UCASAL")
            return False
    except Exception as e:
        print_status(False, f"Error: {e}")
        return False

def test_bfaresponse(titulo_uuid, status="success"):
    """Probar callback de blockchain"""
    print_section(f"CALLBACK BLOCKCHAIN - Título {titulo_uuid} ({status})")
    
    try:
        response = requests.post(
            f"{BASE_URL}/titulos/{titulo_uuid}/bfaresponse/",
            json={"status": status},
            timeout=10
        )
        
        if response.status_code == 200:
            print_status(True, f"Callback procesado: {response.text[:100]}")
            return True
        else:
            print_status(False, f"Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:300]}")
            return False
    except Exception as e:
        print_status(False, f"Error: {e}")
        return False

def test_recibir_titulo():
    """Probar recibir título (requiere PDF real)"""
    print_section("RECIBIR TÍTULO (requiere PDF)")
    
    # Crear un PDF de prueba simple
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF'
    
    try:
        files = {
            'file': ('titulo_test.pdf', pdf_content, 'application/pdf')
        }
        data = {
            'filename': '8205853/10/3/16/2/8707',  # DNI/Lugar/SECTOR/CARRERA/MODO/PLAN
            'serie': 'títulos',
            'doctype': 'títulos',
            'json_data': json.dumps({
                'DNI': '8205853',
                'Tipo DNI': 'DNI',
                'Lugar': '10',
                'Facultad': '3',
                'Carrera': '16',
                'Modalidad': '2',
                'Plan': '8707',
                'Título': 'Abogado'
            })
        }
        
        response = requests.post(
            f"{BASE_URL}/titulos/recibir/",
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            data_resp = response.json()
            print_status(True, f"Título recibido: {data_resp.get('uuid', 'N/A')}")
            print(f"   Filename: {data_resp.get('filename', 'N/A')}")
            return data_resp.get('uuid')
        else:
            print_status(False, f"Status: {response.status_code}")
            print(f"   Respuesta: {response.text[:300]}")
            print("[INFO] Nota: Este endpoint requiere conexión con Athento")
            return None
    except Exception as e:
        print_status(False, f"Error: {e}")
        return None

def main():
    print("\n" + "PRUEBAS DE ENDPOINTS DE TÍTULOS".center(70))
    print("=" * 70)
    
    # Verificar servidor
    try:
        check_timeout = 5 if IS_REMOTE else 2
        requests.get(f"{BASE_URL}/", timeout=check_timeout)
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
    
    # Obtener títulos existentes
    print_section("OBTENIENDO TÍTULOS EXISTENTES")
    titulos = obtener_titulos_existentes()
    
    if not titulos:
        print("[INFO] No hay títulos existentes.")
        print("[INFO] Ejecuta primero: python crear_titulos_prueba.py")
        print("\n[INFO] Probando endpoints que no requieren títulos previos...")
    else:
        print(f"[OK] Se encontraron {len(titulos)} títulos")
        for i, titulo in enumerate(titulos, 1):
            print(f"   {i}. {titulo['titulo']} ({titulo['estado']}) - {titulo['uuid']}")
    
    # Probar endpoints
    resultados = []
    
    # 1. Generar QR (no requiere título previo)
    resultados.append(("qr", test_qr()))
    
    # 2. Recibir título (puede fallar si no hay Athento)
    nuevo_uuid = test_recibir_titulo()
    if nuevo_uuid:
        titulos.append({'uuid': nuevo_uuid, 'titulo': 'Título Nuevo', 'estado': 'Recibido'})
    
    # 3. Probar con títulos existentes
    if titulos:
        # Buscar título en estado recibido para informar estado
        titulo_recibido = next((t for t in titulos if 'recibido' in t['estado'].lower()), None)
        if titulo_recibido:
            resultados.append(("informar_estado", test_informar_estado(
                titulo_recibido['uuid'], 
                "Pendiente Aprobación UA"
            )))
        
        # Buscar título para validar OTP
        titulo_otp = titulos[0] if titulos else None
        if titulo_otp:
            print("[INFO] Nota: Usando OTP mock. En producción, usar OTP real del servicio UCASAL.")
            resultados.append(("validar_otp", test_validar_otp(titulo_otp['uuid'], 123456)))
        
        # Buscar título en estado pendiente_blockchain para callback
        titulo_blockchain = next((t for t in titulos if 'blockchain' in t['estado'].lower()), None)
        if titulo_blockchain:
            resultados.append(("bfaresponse", test_bfaresponse(titulo_blockchain['uuid'], "success")))
    
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
        print("\n[INFO] Notas importantes:")
        print("   - Algunos endpoints requieren servicios externos (Athento, UCASAL, Blockchain)")
        print("   - Los OTPs deben ser válidos del servicio UCASAL")
        print("   - Para recibir títulos se necesita conexión con Athento")
    else:
        print("\n[INFO] No se pudieron ejecutar pruebas. Crea títulos primero:")
        print("       1. Ejecuta: python crear_titulos_prueba.py")
        print("       2. O crea títulos desde el admin: http://localhost:8012/admin/")

if __name__ == "__main__":
    main()

