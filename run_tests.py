#!/usr/bin/env python
"""
Script para ejecutar tests del proyecto UCASAL
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Ejecutar un comando y mostrar el resultado"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        if e.stdout:
            print(f"Salida: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    """Función principal de testing"""
    
    print("🧪 Ejecutando tests del proyecto UCASAL...")
    print("=" * 50)
    
    # Verificar que estamos en el directorio correcto
    if not Path('manage.py').exists():
        print("❌ Error: No se encontró manage.py. Asegúrate de estar en el directorio raíz del proyecto.")
        sys.exit(1)
    
    # Configurar variables de entorno
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ucasal.test_settings')
    
    # Verificar que el entorno virtual esté activado
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Advertencia: No parece que estés usando un entorno virtual.")
        print("   Se recomienda activar el entorno virtual antes de continuar.")
        response = input("¿Continuar de todas formas? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Ejecutar tests
    test_commands = [
        ("python manage.py test endpoints.actas.tests.test_models --verbosity=2", "Tests de modelos"),
        ("python manage.py test endpoints.actas.tests.test_endpoints --verbosity=2", "Tests de endpoints"),
        ("python manage.py test endpoints.actas.tests.test_admin --verbosity=2", "Tests de admin"),
        ("python manage.py test --verbosity=2", "Todos los tests"),
    ]
    
    success_count = 0
    total_count = len(test_commands)
    
    for command, description in test_commands:
        if run_command(command, description):
            success_count += 1
        print("-" * 30)
    
    print(f"\n📊 Resumen de tests:")
    print(f"✅ Exitosos: {success_count}/{total_count}")
    print(f"❌ Fallidos: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 ¡Todos los tests pasaron exitosamente!")
        sys.exit(0)
    else:
        print("⚠️  Algunos tests fallaron. Revisa los errores arriba.")
        sys.exit(1)

if __name__ == '__main__':
    main()
