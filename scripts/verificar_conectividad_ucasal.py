#!/usr/bin/env python
"""
Script para verificar la conectividad con los servicios UCASAL.
Prueba todos los endpoints externos configurados y valida las credenciales.
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Cargar variables de entorno
load_dotenv()

# Importar configuración
try:
    from ucasal.sp_athento_config import SpAthentoConfig as SAC
except ImportError:
    from ucasal.mocks.sp_athento_config import SpAthentoConfig as SAC

from ucasal.utils import UcasalConfig
from external_services.ucasal.ucasal_services import UcasalServices


class Colors:
    """Códigos de color para terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Imprime un encabezado formateado"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_test(name, status, message="", details=""):
    """Imprime el resultado de una prueba"""
    if status:
        icon = f"{Colors.GREEN}✓{Colors.RESET}"
        status_text = f"{Colors.GREEN}OK{Colors.RESET}"
    else:
        icon = f"{Colors.RED}✗{Colors.RESET}"
        status_text = f"{Colors.RED}FAIL{Colors.RESET}"
    
    print(f"  {icon} {name:.<50} {status_text}")
    if message:
        print(f"     {message}")
    if details:
        print(f"     {Colors.BLUE}→{Colors.RESET} {details}")


def test_variables_entorno():
    """Verifica que todas las variables de entorno necesarias estén configuradas"""
    print_header("VERIFICACIÓN DE VARIABLES DE ENTORNO")
    
    variables_requeridas = [
        'UCASAL_TOKEN_SVC_URL',
        'UCASAL_TOKEN_SVC_USER',
        'UCASAL_TOKEN_SVC_PASSWORD',
        'UCASAL_QR_SVC_URL',
        'UCASAL_SHORTEN_URL_SVC_URL',
    ]
    
    todas_ok = True
    for var in variables_requeridas:
        valor = os.getenv(var)
        if valor:
            print_test(var, True, f"Configurado: {valor[:50]}...")
        else:
            print_test(var, False, "No configurado")
            todas_ok = False
    
    return todas_ok


def test_configuracion_cargada():
    """Verifica que la configuración se carga correctamente"""
    print_header("VERIFICACIÓN DE CONFIGURACIÓN")
    
    configs = {
        'Token Service URL': UcasalConfig.token_svc_url(),
        'Token Service User': UcasalConfig.token_svc_user(),
        'QR Service URL': UcasalConfig.qr_svc_url(),
        'Shorten URL Service': UcasalConfig.shorten_url_svc_url(),
        'Shorten URL Env': UcasalConfig.shorten_url_svc_env(),
        'Acta Validation Template': UcasalConfig.acta_validation_url_template(),
        'Titulo Validation Template': UcasalConfig.titulo_validation_url_template(),
    }
    
    todas_ok = True
    for name, value in configs.items():
        if value:
            print_test(name, True, f"Valor: {value[:60]}...")
        else:
            print_test(name, False, "Valor vacío o no configurado")
            todas_ok = False
    
    return todas_ok


def test_conectividad_urls():
    """Prueba la conectividad básica con las URLs de los servicios"""
    print_header("VERIFICACIÓN DE CONECTIVIDAD (URLs)")
    
    urls = {
        'Token Service': UcasalConfig.token_svc_url(),
        'QR Service': UcasalConfig.qr_svc_url(),
        'Shorten URL Service': UcasalConfig.shorten_url_svc_url(),
    }
    
    resultados = {}
    for name, url in urls.items():
        try:
            # Intentar HEAD request (más rápido que GET)
            response = requests.head(url, timeout=5, allow_redirects=True)
            resultados[name] = (True, f"Status: {response.status_code}")
            print_test(name, True, f"Conectado - Status: {response.status_code}")
        except requests.exceptions.Timeout:
            resultados[name] = (False, "Timeout")
            print_test(name, False, "Timeout al conectar")
        except requests.exceptions.ConnectionError:
            resultados[name] = (False, "Error de conexión")
            print_test(name, False, "Error de conexión")
        except Exception as e:
            resultados[name] = (False, str(e))
            print_test(name, False, f"Error: {str(e)[:50]}")
    
    return all(status for status, _ in resultados.values())


def test_autenticacion_token():
    """Prueba la autenticación con el servicio de token"""
    print_header("VERIFICACIÓN DE AUTENTICACIÓN")
    
    try:
        user = UcasalConfig.token_svc_user()
        password = UcasalConfig.token_svc_password()
        
        if not user or not password:
            print_test("Token Service Auth", False, "Credenciales no configuradas")
            return False
        
        print(f"  🔄 Intentando autenticación con usuario: {user[:20]}...")
        
        token = UcasalServices.get_auth_token(user, password)
        
        if token:
            print_test("Token Service Auth", True, f"Token obtenido: {token[:30]}...")
            return True
        else:
            print_test("Token Service Auth", False, "No se pudo obtener token")
            return False
            
    except Exception as e:
        print_test("Token Service Auth", False, f"Error: {str(e)[:100]}")
        return False


def test_generacion_qr():
    """Prueba la generación de un QR code"""
    print_header("VERIFICACIÓN DE GENERACIÓN DE QR")
    
    try:
        # Obtener token primero
        user = UcasalConfig.token_svc_user()
        password = UcasalConfig.token_svc_password()
        
        if not user or not password:
            print_test("Generación QR", False, "Credenciales no configuradas")
            return False
        
        token = UcasalServices.get_auth_token(user, password)
        if not token:
            print_test("Generación QR", False, "No se pudo obtener token de autenticación")
            return False
        
        # Probar generación de QR
        test_url = "https://www.ucasal.edu.ar/test"
        print(f"  🔄 Generando QR para URL: {test_url}")
        
        qr_data = UcasalServices.get_qr_image(url=test_url)
        
        if qr_data:
            if isinstance(qr_data, bytes):
                size = len(qr_data)
            else:
                size = len(qr_data.getvalue()) if hasattr(qr_data, 'getvalue') else 0
            
            print_test("Generación QR", True, f"QR generado: {size} bytes")
            return True
        else:
            print_test("Generación QR", False, "No se pudo generar QR")
            return False
            
    except Exception as e:
        print_test("Generación QR", False, f"Error: {str(e)[:100]}")
        return False


def test_acortar_url():
    """Prueba el servicio de acortar URLs"""
    print_header("VERIFICACIÓN DE ACORTAR URL")
    
    try:
        # Obtener token primero
        user = UcasalConfig.token_svc_user()
        password = UcasalConfig.token_svc_password()
        
        if not user or not password:
            print_test("Acortar URL", False, "Credenciales no configuradas")
            return False
        
        token = UcasalServices.get_auth_token(user, password)
        if not token:
            print_test("Acortar URL", False, "No se pudo obtener token de autenticación")
            return False
        
        # Probar acortar URL
        test_url = "https://www.ucasal.edu.ar/test/very/long/url/to/shorten"
        print(f"  🔄 Acortando URL: {test_url[:50]}...")
        
        short_url = UcasalServices.get_short_url(auth_token=token, url=test_url)
        
        if short_url:
            print_test("Acortar URL", True, f"URL acortada: {short_url}")
            return True
        else:
            print_test("Acortar URL", False, "No se pudo acortar URL")
            return False
            
    except Exception as e:
        print_test("Acortar URL", False, f"Error: {str(e)[:100]}")
        return False


def main():
    """Función principal"""
    print("\n" + f"{Colors.BOLD}🔍 VERIFICACIÓN DE CONECTIVIDAD UCASAL{Colors.RESET}".center(70))
    print("=" * 70)
    
    resultados = {}
    
    # 1. Verificar variables de entorno
    resultados['variables'] = test_variables_entorno()
    
    # 2. Verificar configuración cargada
    resultados['configuracion'] = test_configuracion_cargada()
    
    # 3. Verificar conectividad básica
    resultados['conectividad'] = test_conectividad_urls()
    
    # 4. Verificar autenticación
    resultados['autenticacion'] = test_autenticacion_token()
    
    # 5. Verificar generación de QR (solo si autenticación OK)
    if resultados['autenticacion']:
        resultados['qr'] = test_generacion_qr()
    else:
        print_header("VERIFICACIÓN DE GENERACIÓN DE QR")
        print_test("Generación QR", False, "Omitido: Autenticación falló")
        resultados['qr'] = False
    
    # 6. Verificar acortar URL (solo si autenticación OK)
    if resultados['autenticacion']:
        resultados['acortar_url'] = test_acortar_url()
    else:
        print_header("VERIFICACIÓN DE ACORTAR URL")
        print_test("Acortar URL", False, "Omitido: Autenticación falló")
        resultados['acortar_url'] = False
    
    # Resumen final
    print_header("RESUMEN")
    
    total = len(resultados)
    exitosos = sum(1 for v in resultados.values() if v)
    
    print(f"\n  Pruebas exitosas: {Colors.GREEN}{exitosos}/{total}{Colors.RESET}")
    
    for nombre, resultado in resultados.items():
        status_icon = f"{Colors.GREEN}✓{Colors.RESET}" if resultado else f"{Colors.RED}✗{Colors.RESET}"
        print(f"  {status_icon} {nombre.replace('_', ' ').title()}")
    
    if exitosos == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Todas las verificaciones pasaron exitosamente{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Algunas verificaciones fallaron{Colors.RESET}")
        print(f"\n💡 Revisa la configuración en el archivo .env")
        print(f"   Ejecuta: python scripts/configurar_ambiente_ucasal.py")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Verificación cancelada por el usuario{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error durante la verificación: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

