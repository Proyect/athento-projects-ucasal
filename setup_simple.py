#!/usr/bin/env python
"""
Script de configuración inicial del proyecto UCASAL (versión simplificada)
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Ejecutar un comando y mostrar el resultado"""
    print(f"[INFO] {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"[OK] {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error en {description}: {e}")
        if e.stdout:
            print(f"Salida: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    """Función principal de configuración"""
    
    print("Configurando proyecto UCASAL...")
    print("=" * 50)
    
    # Verificar que estamos en el directorio correcto
    if not Path('manage.py').exists():
        print("Error: No se encontró manage.py. Asegúrate de estar en el directorio raíz del proyecto.")
        sys.exit(1)
    
    # Configurar variables de entorno
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ucasal.development_settings')
    
    # 1. Verificar que el entorno virtual esté activado
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("Advertencia: No parece que estés usando un entorno virtual.")
        print("Se recomienda crear y activar un entorno virtual antes de continuar.")
        response = input("¿Continuar de todas formas? (y/N): ")
        if response.lower() != 'y':
            print("Para crear un entorno virtual, ejecuta:")
            print("   python -m venv .venv")
            print("   .venv\\Scripts\\activate  # Windows")
            print("   source .venv/bin/activate  # Linux/Mac")
            sys.exit(1)
    
    # 2. Instalar dependencias
    if not run_command("pip install -r requirements.txt", "Instalando dependencias"):
        sys.exit(1)
    
    # 3. Crear archivo .env si no existe
    if not Path('.env').exists():
        if Path('env.example').exists():
            run_command("copy env.example .env", "Creando archivo .env desde env.example")
        else:
            print("No se encontró env.example. Creando .env básico...")
            with open('.env', 'w') as f:
                f.write("""# Django Configuration
DJANGO_SECRET_KEY=dev-secret-key-change-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration
DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=ucasal/db.sqlite3

# Media Configuration
MEDIA_ROOT=media
MEDIA_TMP=tmp

# UCASAL Configuration
UCASAL_TOKEN_SVC_URL=https://api.ucasal.edu.ar/token
UCASAL_TOKEN_SVC_USER=test_user
UCASAL_TOKEN_SVC_PASSWORD=test_password
UCASAL_QR_SVC_URL=https://api.ucasal.edu.ar/qr
UCASAL_STAMPS_SVC_URL=https://api.ucasal.edu.ar/stamps
UCASAL_CHANGE_ACTA_SVC_URL=https://api.ucasal.edu.ar/change-acta
UCASAL_SHORTEN_URL_SVC_URL=https://api.ucasal.edu.ar/shorten
UCASAL_SHORTEN_URL_SVC_ENV=desarrollo
UCASAL_ACTA_VALIDATION_URL_TEMPLATE=https://ucasal.edu.ar/validar/{{uuid}}
UCASAL_OTP_VALIDATION_URL_TEMPLATE=https://api.ucasal.edu.ar/otp/validate?usuario={{usuario}}&token={{token}}
UCASAL_OTP_VALIDITY_SECONDS=300
""")
    
    # 4. Crear directorios necesarios
    directories = ['media', 'tmp', 'logs', 'staticfiles']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"[OK] Directorio {directory} creado/verificado")
    
    # 5. Ejecutar migraciones
    if not run_command("python manage.py migrate", "Ejecutando migraciones de base de datos"):
        sys.exit(1)
    
    # 6. Verificar configuración
    if not run_command("python manage.py check", "Verificando configuración de Django"):
        print("Se encontraron problemas en la configuración, pero continuando...")
    
    # 7. Crear superusuario si no existe
    print("Verificando superusuario...")
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            print("Creando superusuario...")
            print("   Usuario: admin")
            print("   Email: admin@example.com")
            print("   Contraseña: admin123")
            
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            print("[OK] Superusuario creado exitosamente")
        else:
            print("[OK] Superusuario ya existe")
    except Exception as e:
        print(f"No se pudo verificar/crear superusuario: {e}")
    
    print("\n" + "=" * 50)
    print("Configuración completada exitosamente!")
    print("\nPróximos pasos:")
    print("1. Iniciar el servidor: python manage.py runserver 8012")
    print("2. Acceder a la aplicación: http://localhost:8012")
    print("3. Panel de administración: http://localhost:8012/admin/")
    print("4. Documentación API: http://localhost:8012/docs/")
    print("\nCredenciales de administración:")
    print("   Usuario: admin")
    print("   Contraseña: admin123")

if __name__ == '__main__':
    main()
