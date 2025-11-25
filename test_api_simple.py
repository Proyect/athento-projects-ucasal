#!/usr/bin/env python
"""
Script simple para probar la API de UCASAL
Soporta tanto ambiente local como remoto (UAT/Producción)
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8012")
ADMIN_USERNAME = os.getenv("API_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("API_ADMIN_PASSWORD", "admin123")

# Detectar si es ambiente remoto para ajustar timeouts
IS_REMOTE = BASE_URL.startswith("https://")
DEFAULT_TIMEOUT = 30 if IS_REMOTE else 5

def print_section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

def test_basic_endpoints():
    """Probar endpoints básicos que no requieren autenticación"""
    
    print_section("1. INFORMACIÓN DE API")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=DEFAULT_TIMEOUT)
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout al conectar con {BASE_URL}")
        print("        Verifica la conectividad o aumenta el timeout")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] No se pudo conectar a {BASE_URL}")
        print("        Verifica que el servidor esté disponible")
    except Exception as e:
        print(f"[ERROR] Error: {e}")
    
    print_section("2. DOCUMENTACIÓN")
    try:
        response = requests.get(f"{BASE_URL}/docs/", timeout=DEFAULT_TIMEOUT)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Title: {data.get('title')}")
        print(f"Endpoints disponibles: {len(data.get('endpoints', {}))}")
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout al conectar")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Error de conexión")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

def test_auth():
    """Probar autenticación JWT"""
    print_section("3. AUTENTICACIÓN JWT")
    
    # Intentar login (puede fallar si no existe usuario 'admin')
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login/",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=DEFAULT_TIMEOUT
        )
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access", "")[:50]
            print(f"[OK] Token obtenido: {token}...")
            return token_data.get("access")
        else:
            print(f"[INFO] Login falló (posible que necesites crear usuario): {response.status_code}")
            print(response.text[:200])
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout al intentar autenticación")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Error de conexión al intentar autenticación")
    except Exception as e:
        print(f"[ERROR] Error en login: {e}")
    
    return None

def test_qr():
    """Probar generación de QR"""
    print_section("4. GENERAR QR")
    
    try:
        qr_timeout = DEFAULT_TIMEOUT * 2  # QR puede tardar más
        response = requests.post(
            f"{BASE_URL}/actas/qr/",
            json={"url": "https://www.ucasal.edu.ar/test"},
            timeout=qr_timeout
        )
        if response.status_code == 200:
            print(f"[OK] QR generado: {len(response.content)} bytes")
            # Guardar imagen si es posible
            try:
                with open("qr_test.png", "wb") as f:
                    f.write(response.content)
                print("[OK] Imagen guardada en qr_test.png")
            except:
                print("[INFO] No se pudo guardar imagen")
        else:
            print(f"[ERROR] Status: {response.status_code}")
            print(response.text[:200])
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout al generar QR (puede tardar más en ambiente remoto)")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Error de conexión al generar QR")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

def test_getconfig():
    """Probar obtener configuración"""
    print_section("5. OBTENER CONFIGURACIÓN")
    
    try:
        response = requests.post(
            f"{BASE_URL}/actas/getconfig/",
            json={"key": "test_key", "is_secret": False},
            timeout=DEFAULT_TIMEOUT
        )
        if response.status_code == 200:
            print(f"[OK] Configuración: {response.text[:100]}")
        else:
            print(f"[ERROR] Status: {response.status_code}")
            print(response.text[:200])
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout al obtener configuración")
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Error de conexión")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

def main():
    print("\n" + "PRUEBAS DEL SISTEMA UCASAL".center(60))
    print("=" * 60)
    print(f"Ambiente: {'REMOTO' if IS_REMOTE else 'LOCAL'}")
    print(f"URL Base: {BASE_URL}")
    print(f"Timeout: {DEFAULT_TIMEOUT}s")
    
    # Verificar que el servidor está disponible
    try:
        check_timeout = 5 if IS_REMOTE else 2
        requests.get(f"{BASE_URL}/", timeout=check_timeout)
        print("[OK] Servidor disponible")
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout: Servidor no responde en {BASE_URL}")
        if not IS_REMOTE:
            print("        Ejecuta: python manage.py runserver 8012")
        else:
            print("        Verifica la conectividad de red")
        return
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] No se pudo conectar a {BASE_URL}")
        if not IS_REMOTE:
            print("        Ejecuta: python manage.py runserver 8012")
        else:
            print("        Verifica la URL y la conectividad")
        return
    except Exception as e:
        print(f"[ERROR] Error al verificar servidor: {e}")
        return
    
    # Ejecutar pruebas
    test_basic_endpoints()
    token = test_auth()
    test_qr()
    test_getconfig()
    
    print_section("RESUMEN")
    print("[INFO] Para pruebas completas:")
    print("       1. Crea actas desde el admin: http://localhost:8012/admin/")
    print("       2. Usa los UUIDs de las actas para probar endpoints específicos")
    print("       3. Revisa GUIA_PRUEBAS_SISTEMA.md para más detalles")

if __name__ == "__main__":
    main()

