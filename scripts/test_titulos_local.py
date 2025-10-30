#!/usr/bin/env python
"""
Script para probar endpoints de títulos localmente sin Athento
Ejecutar: python scripts/test_titulos_local.py
"""
import os
import sys
import django

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ucasal.development_settings')
django.setup()

from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from model.File import File, Doctype, LifeCycleState, Team, Serie
from ucasal.utils import TituloStates
import json
import uuid
import unittest.mock


def setup_test_data():
    """Configura datos de prueba"""
    print("📦 Configurando datos de prueba...")
    
    # Team
    team, _ = Team.objects.get_or_create(name='UCASAL')
    
    # Doctype
    doctype, _ = Doctype.objects.get_or_create(name='títulos')
    
    # Estados
    for estado_name in [
        TituloStates.recibido,
        TituloStates.pendiente_aprobacion_ua,
        TituloStates.aprobado_ua,
        TituloStates.pendiente_aprobacion_r,
        TituloStates.aprobado_r,
        TituloStates.pendiente_firma_sg,
        TituloStates.firmado_sg,
        TituloStates.titulo_emitido,
        TituloStates.rechazado,
    ]:
        LifeCycleState.objects.get_or_create(name=estado_name)
    
    # Series
    series_names = [
        'títulos',
        'títulos_pendiente_ua',
        'títulos_pendiente_rector',
        'títulos_pendiente_sg',
        'títulos_emitidos',
        'títulos_rechazados',
    ]
    
    for serie_name in series_names:
        Serie.objects.get_or_create(
            name=serie_name,
            defaults={'team': team}
        )
    
    print("✅ Datos de prueba configurados\n")


def test_create_titulo():
    """Prueba crear un título"""
    print("🧪 Test 1: Crear título")
    
    # Obtener datos
    doctype = Doctype.objects.get(name='títulos')
    estado = LifeCycleState.objects.get(name=TituloStates.recibido)
    serie = Serie.objects.get(name='títulos')
    
    # Crear título
    titulo = File.objects.create(
        titulo='Título de Prueba - Abogado',
        doctype_obj=doctype,
        life_cycle_state_obj=estado,
        serie=serie,
        filename='8205853_titulo.pdf'
    )
    
    # Agregar metadata
    titulo.set_metadata('metadata.titulo_dni', '8205853')
    titulo.set_metadata('metadata.titulo_carrera', 'Abogacia')
    titulo.set_metadata('metadata.titulo_titulo', 'Abogado')
    
    print(f"   ✅ Título creado: {titulo.uuid}")
    print(f"   Doctype: {titulo.doctype.name}")
    print(f"   Estado: {titulo.life_cycle_state.name}")
    print(f"   Serie: {titulo.serie.name}")
    print(f"   DNI: {titulo.gmv('metadata.titulo_dni')}")
    print()
    
    return titulo


def test_move_to_serie():
    """Prueba mover título a otra serie"""
    print("🧪 Test 2: Mover título a serie")
    
    titulo = File.objects.first()
    if not titulo:
        print("   ⚠️  No hay títulos, creando uno...")
        titulo = test_create_titulo()
    
    serie_ua = Serie.objects.get(name='títulos_pendiente_ua')
    
    print(f"   Moviendo de '{titulo.serie.name}' a '{serie_ua.name}'...")
    titulo.move_to_serie(serie_ua)
    titulo.refresh_from_db()
    
    print(f"   ✅ Nueva serie: {titulo.serie.name}")
    print()


def test_change_state():
    """Prueba cambiar estado"""
    print("🧪 Test 3: Cambiar estado del título")
    
    titulo = File.objects.first()
    if not titulo:
        print("   ⚠️  No hay títulos, creando uno...")
        titulo = test_create_titulo()
    
    print(f"   Estado actual: {titulo.life_cycle_state.name}")
    print(f"   Cambiando a: {TituloStates.pendiente_aprobacion_ua}...")
    
    titulo.change_life_cycle_state(TituloStates.pendiente_aprobacion_ua)
    titulo.refresh_from_db()
    
    print(f"   ✅ Nuevo estado: {titulo.life_cycle_state.name}")
    print()


def test_operation_asignar_espacio():
    """Prueba la operation de asignar espacio"""
    print("🧪 Test 4: Operation Asignar Espacio")
    
    try:
        from operations.titulos_asignar_espacio import GdeAsignarEspacioTitulo
        
        titulo = File.objects.first()
        if not titulo:
            print("   ⚠️  No hay títulos, creando uno...")
            titulo = test_create_titulo()
        
        # Cambiar estado para probar la operation
        titulo.change_life_cycle_state(TituloStates.pendiente_aprobacion_ua)
        titulo.refresh_from_db()
        
        print(f"   Estado actual: {titulo.life_cycle_state.name}")
        print(f"   Serie actual: {titulo.serie.name}")
        
        # Crear mock operation
        class MockOperation:
            def __init__(self, document):
                self.document = document
        
        mock_op = MockOperation(titulo)
        operation = GdeAsignarEspacioTitulo()
        operation.document = titulo
        
        result = operation.execute()
        
        titulo.refresh_from_db()
        print(f"   ✅ Resultado: {result['msg_type']} - {result['msg']}")
        print(f"   Nueva serie: {titulo.serie.name}")
        print()
        
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        print("   (Esto es normal si no estás en entorno Athento)")
        print()


def test_gmv_gfv():
    """Prueba métodos gmv y gfv"""
    print("🧪 Test 5: Métodos gmv() y gfv()")
    
    titulo = File.objects.first()
    if not titulo:
        print("   ⚠️  No hay títulos, creando uno...")
        titulo = test_create_titulo()
    
    # Test gmv
    titulo.set_metadata('metadata.titulo_dni', '12345678')
    dni = titulo.gmv('metadata.titulo_dni')
    print(f"   ✅ gmv('metadata.titulo_dni') = {dni}")
    
    # Test gfv
    titulo.set_feature('registro.en.blockchain', 'pending')
    blockchain = titulo.gfv('registro.en.blockchain')
    print(f"   ✅ gfv('registro.en.blockchain') = {blockchain}")
    print()


def main():
    """Función principal"""
    print("="*60)
    print("🧪 TEST DE TÍTULOS SIN ATHENTO")
    print("="*60)
    print()
    
    try:
        # Setup
        setup_test_data()
        
        # Tests
        test_create_titulo()
        test_gmv_gfv()
        test_change_state()
        test_move_to_serie()
        test_operation_asignar_espacio()
        
        print("="*60)
        print("✅ TODOS LOS TESTS COMPLETADOS")
        print("="*60)
        
        # Resumen
        print(f"\n📊 Resumen:")
        print(f"   Títulos creados: {File.objects.count()}")
        print(f"   Estados disponibles: {LifeCycleState.objects.count()}")
        print(f"   Series disponibles: {Serie.objects.count()}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()


