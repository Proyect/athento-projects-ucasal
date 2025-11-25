#!/usr/bin/env python
"""
Script interactivo para configurar el ambiente de UCASAL.
Permite seleccionar entre ambiente Local, UAT o Producción y configura el archivo .env
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv, set_key, find_dotenv

# Configuraciones predefinidas por ambiente
AMBIENTES = {
    'local': {
        'name': 'Local (Desarrollo)',
        'api_base_url': 'http://localhost:8012',
        'token_svc_url': 'https://ucasal-uat.athento.com/token',
        'qr_svc_url': 'https://ucasal-uat.athento.com/qr',
        'stamps_svc_url': 'https://ucasal-uat.athento.com/stamps',
        'change_acta_svc_url': 'https://ucasal-uat.athento.com/change-acta',
        'shorten_url_svc_url': 'https://ucasal-uat.athento.com/shorten',
        'shorten_url_svc_env': 'desarrollo',
        'acta_validation_url_template': 'https://ucasal-uat.athento.com/validar/{{uuid}}',
        'otp_validation_url_template': 'https://ucasal-uat.athento.com/otp/validate?usuario={{usuario}}&token={{token}}',
        'titulo_validation_url_template': 'https://www.ucasal.edu.ar/validar/index.php?d=titulo&e=testing&uuid={{uuid}}',
    },
    'uat': {
        'name': 'UAT (Testing)',
        'api_base_url': 'https://ucasal-uat.athento.com',
        'token_svc_url': 'https://ucasal-uat.athento.com/token',
        'qr_svc_url': 'https://ucasal-uat.athento.com/qr',
        'stamps_svc_url': 'https://ucasal-uat.athento.com/stamps',
        'change_acta_svc_url': 'https://ucasal-uat.athento.com/change-acta',
        'shorten_url_svc_url': 'https://ucasal-uat.athento.com/shorten',
        'shorten_url_svc_env': 'desarrollo',
        'acta_validation_url_template': 'https://ucasal-uat.athento.com/validar/{{uuid}}',
        'otp_validation_url_template': 'https://ucasal-uat.athento.com/otp/validate?usuario={{usuario}}&token={{token}}',
        'titulo_validation_url_template': 'https://www.ucasal.edu.ar/validar/index.php?d=titulo&e=testing&uuid={{uuid}}',
    },
    'produccion': {
        'name': 'Producción',
        'api_base_url': 'https://api.ucasal.edu.ar',
        'token_svc_url': 'https://api.ucasal.edu.ar/token',
        'qr_svc_url': 'https://api.ucasal.edu.ar/qr',
        'stamps_svc_url': 'https://api.ucasal.edu.ar/stamps',
        'change_acta_svc_url': 'https://api.ucasal.edu.ar/change-acta',
        'shorten_url_svc_url': 'https://api.ucasal.edu.ar/shorten',
        'shorten_url_svc_env': 'produccion',
        'acta_validation_url_template': 'https://ucasal.edu.ar/validar/{{uuid}}',
        'otp_validation_url_template': 'https://api.ucasal.edu.ar/otp/validate?usuario={{usuario}}&token={{token}}',
        'titulo_validation_url_template': 'https://www.ucasal.edu.ar/validar/index.php?d=titulo&uuid={{uuid}}',
    }
}

# Variables que requieren input del usuario
VARIABLES_REQUERIDAS = {
    'UCASAL_TOKEN_SVC_USER': 'Usuario para servicio de token UCASAL',
    'UCASAL_TOKEN_SVC_PASSWORD': 'Contraseña para servicio de token UCASAL',
    'API_ADMIN_USERNAME': 'Usuario administrador de la API',
    'API_ADMIN_PASSWORD': 'Contraseña del usuario administrador',
}


def print_header(text):
    """Imprime un encabezado formateado"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def seleccionar_ambiente():
    """Permite al usuario seleccionar el ambiente"""
    print_header("SELECCIÓN DE AMBIENTE")
    print("\nSelecciona el ambiente a configurar:\n")
    
    for key, config in AMBIENTES.items():
        print(f"  [{key[0].upper()}] {config['name']}")
    
    while True:
        seleccion = input("\nOpción (l/u/p): ").lower().strip()
        
        if seleccion in ['l', 'local']:
            return 'local'
        elif seleccion in ['u', 'uat']:
            return 'uat'
        elif seleccion in ['p', 'produccion', 'prod']:
            return 'produccion'
        else:
            print("❌ Opción inválida. Por favor selecciona l, u o p.")


def obtener_credenciales():
    """Solicita las credenciales necesarias al usuario"""
    print_header("CREDENCIALES")
    print("\nIngresa las credenciales necesarias (presiona Enter para mantener valores existentes):\n")
    
    credenciales = {}
    env_file = find_dotenv()
    
    # Cargar valores existentes si el archivo existe
    valores_existentes = {}
    if env_file:
        load_dotenv(env_file)
        for var in VARIABLES_REQUERIDAS.keys():
            valores_existentes[var] = os.getenv(var, '')
    
    for var, descripcion in VARIABLES_REQUERIDAS.items():
        valor_actual = valores_existentes.get(var, '')
        if valor_actual:
            prompt = f"{descripcion} [{valor_actual[:10]}...]: "
        else:
            prompt = f"{descripcion}: "
        
        valor = input(prompt).strip()
        
        if valor:
            credenciales[var] = valor
        elif valor_actual:
            credenciales[var] = valor_actual
        else:
            print(f"⚠️  Advertencia: {var} no fue proporcionado. Deberás configurarlo manualmente.")
            credenciales[var] = ''
    
    return credenciales


def configurar_env(ambiente, credenciales):
    """Configura el archivo .env con los valores del ambiente seleccionado"""
    print_header("CONFIGURANDO ARCHIVO .ENV")
    
    env_file = find_dotenv()
    if not env_file:
        env_file = BASE_DIR / '.env'
        # Crear archivo .env si no existe
        if not env_file.exists():
            env_file.touch()
            print(f"✅ Archivo .env creado en: {env_file}")
    
    config = AMBIENTES[ambiente]
    
    # Variables de configuración del ambiente
    variables_ambiente = {
        'API_BASE_URL': config['api_base_url'],
        'UCASAL_TOKEN_SVC_URL': config['token_svc_url'],
        'UCASAL_QR_SVC_URL': config['qr_svc_url'],
        'UCASAL_STAMPS_SVC_URL': config['stamps_svc_url'],
        'UCASAL_CHANGE_ACTA_SVC_URL': config['change_acta_svc_url'],
        'UCASAL_SHORTEN_URL_SVC_URL': config['shorten_url_svc_url'],
        'UCASAL_SHORTEN_URL_SVC_ENV': config['shorten_url_svc_env'],
        'UCASAL_ACTA_VALIDATION_URL_TEMPLATE': config['acta_validation_url_template'],
        'UCASAL_OTP_VALIDATION_URL_TEMPLATE': config['otp_validation_url_template'],
        'UCASAL_TITULO_VALIDATION_URL_TEMPLATE': config['titulo_validation_url_template'],
        'UCASAL_OTP_VALIDITY_SECONDS': '300',
    }
    
    # Combinar con credenciales
    todas_variables = {**variables_ambiente, **credenciales}
    
    # Escribir al archivo .env
    print(f"\n📝 Configurando variables en: {env_file}\n")
    
    for key, value in todas_variables.items():
        set_key(env_file, key, value)
        print(f"  ✅ {key} = {value[:50]}{'...' if len(str(value)) > 50 else ''}")
    
    print(f"\n✅ Configuración completada para ambiente: {config['name']}")
    return env_file


def validar_conectividad():
    """Opcional: Validar conectividad con servicios"""
    print_header("VALIDACIÓN DE CONECTIVIDAD")
    
    respuesta = input("\n¿Deseas validar la conectividad con los servicios UCASAL ahora? (s/n): ").lower().strip()
    
    if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
        print("\n🔄 Ejecutando verificación de conectividad...")
        print("   (Ejecuta: python scripts/verificar_conectividad_ucasal.py)")
        return True
    return False


def main():
    """Función principal"""
    print("\n" + "🔧 CONFIGURADOR DE AMBIENTE UCASAL".center(70))
    print("=" * 70)
    
    try:
        # 1. Seleccionar ambiente
        ambiente = seleccionar_ambiente()
        
        # 2. Obtener credenciales
        credenciales = obtener_credenciales()
        
        # 3. Configurar .env
        env_file = configurar_env(ambiente, credenciales)
        
        # 4. Ofrecer validación
        if validar_conectividad():
            print("\n💡 Ejecuta el siguiente comando para verificar la conectividad:")
            print(f"   python scripts/verificar_conectividad_ucasal.py")
        
        print_header("CONFIGURACIÓN COMPLETADA")
        print(f"\n✅ Ambiente configurado: {AMBIENTES[ambiente]['name']}")
        print(f"📁 Archivo .env: {env_file}")
        print("\n📋 Próximos pasos:")
        print("   1. Verifica la conectividad: python scripts/verificar_conectividad_ucasal.py")
        print("   2. Ejecuta pruebas: python test_api_simple.py")
        print("   3. Revisa la documentación: docs/TESTING_AMBIENTE_UCASAL.md")
        
    except KeyboardInterrupt:
        print("\n\n❌ Configuración cancelada por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error durante la configuración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

