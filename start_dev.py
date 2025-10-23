#!/usr/bin/env python
"""
Script de inicio para desarrollo del proyecto UCASAL
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """Función principal para iniciar el servidor de desarrollo"""
    
    # Configurar variables de entorno
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ucasal.development_settings')
    
    # Verificar que estamos en el directorio correcto
    if not Path('manage.py').exists():
        print("❌ Error: No se encontró manage.py. Asegúrate de estar en el directorio raíz del proyecto.")
        sys.exit(1)
    
    # Verificar que el entorno virtual esté activado
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Advertencia: No parece que estés usando un entorno virtual.")
        print("   Se recomienda activar el entorno virtual antes de continuar.")
        response = input("¿Continuar de todas formas? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    print("🚀 Iniciando servidor de desarrollo UCASAL...")
    print("📍 Puerto: 8012")
    print("🌐 URL: http://localhost:8012")
    print("📚 Documentación: http://localhost:8012/docs/")
    print("⚙️  Admin: http://localhost:8012/admin/")
    print("=" * 50)
    
    try:
        # Ejecutar el servidor de desarrollo
        subprocess.run([sys.executable, 'manage.py', 'runserver', '8012'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido por el usuario")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al iniciar el servidor: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
