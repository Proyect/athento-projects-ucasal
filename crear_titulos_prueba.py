#!/usr/bin/env python
"""
Script para crear títulos de prueba para testing
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from model.File import File, Doctype, LifeCycleState, Team, Serie
from ucasal.utils import TituloStates
import uuid

def crear_titulos_prueba():
    """Crear títulos de prueba en diferentes estados"""
    
    print("=" * 70)
    print("CREANDO TÍTULOS DE PRUEBA")
    print("=" * 70)
    
    # Asegurar que existan los datos base
    team, _ = Team.objects.get_or_create(name='UCASAL', defaults={'label': 'UCASAL'})
    doctype, _ = Doctype.objects.get_or_create(name='títulos', defaults={'label': 'Títulos Universitarios'})
    
    # Crear estados de títulos
    estados_titulos = [
        TituloStates.recibido,
        TituloStates.pendiente_aprobacion_ua,
        TituloStates.aprobado_ua,
        TituloStates.pendiente_aprobacion_r,
        TituloStates.aprobado_r,
        TituloStates.pendiente_firma_sg,
        TituloStates.firmado_sg,
        TituloStates.pendiente_blockchain,
        TituloStates.registrado_blockchain,
        TituloStates.titulo_emitido,
        TituloStates.rechazado,
    ]
    
    for estado_name in estados_titulos:
        LifeCycleState.objects.get_or_create(name=estado_name)
    
    # Crear series
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
            defaults={'team': team, 'label': serie_name.replace('_', ' ').title()}
        )
    
    titulos_creados = []
    
    # 1. Título en estado "Recibido" - para probar informar estado
    titulo_uuid1 = uuid.uuid4()
    estado1 = LifeCycleState.objects.get(name=TituloStates.recibido)
    serie1 = Serie.objects.get(name='títulos')
    
    titulo1, created1 = File.objects.get_or_create(
        uuid=titulo_uuid1,
        defaults={
            'titulo': 'Título de Prueba - Recibido',
            'estado': TituloStates.recibido,
            'doctype_obj': doctype,
            'life_cycle_state_obj': estado1,
            'serie': serie1,
            'doctype_legacy': 'títulos',
            'life_cycle_state_legacy': TituloStates.recibido,
            'filename': '8205853_titulo.pdf'
        }
    )
    if created1:
        titulo1.set_metadata('metadata.titulo_dni', '8205853')
        titulo1.set_metadata('metadata.titulo_carrera', 'Abogacia')
        titulo1.set_metadata('metadata.titulo_titulo', 'Abogado')
        titulo1.set_metadata('metadata.titulo_lugar', '10')
        titulo1.set_metadata('metadata.titulo_facultad', '3')
        titulo1.set_metadata('metadata.titulo_carrera_id', '16')
        titulo1.set_metadata('metadata.titulo_modalidad', '2')
        titulo1.set_metadata('metadata.titulo_plan', '8707')
        print(f"[OK] Título creado (recibido): {titulo1.uuid}")
    else:
        titulo_uuid1 = titulo1.uuid
        print(f"[INFO] Título ya existe (recibido): {titulo1.uuid}")
    titulos_creados.append(titulo1)
    
    # 2. Título en estado "Pendiente Aprobación UA" - para probar cambio de estado
    titulo_uuid2 = uuid.uuid4()
    estado2 = LifeCycleState.objects.get(name=TituloStates.pendiente_aprobacion_ua)
    serie2 = Serie.objects.get(name='títulos_pendiente_ua')
    
    titulo2, created2 = File.objects.get_or_create(
        titulo='Título de Prueba - Pendiente Aprobación UA',
        defaults={
            'uuid': titulo_uuid2,
            'estado': TituloStates.pendiente_aprobacion_ua,
            'doctype_obj': doctype,
            'life_cycle_state_obj': estado2,
            'serie': serie2,
            'doctype_legacy': 'títulos',
            'life_cycle_state_legacy': TituloStates.pendiente_aprobacion_ua,
            'filename': '8205854_titulo.pdf'
        }
    )
    if created2:
        titulo2.set_metadata('metadata.titulo_dni', '8205854')
        titulo2.set_metadata('metadata.titulo_carrera', 'Ingeniería')
        titulo2.set_metadata('metadata.titulo_titulo', 'Ingeniero')
        print(f"[OK] Título creado (pendiente_aprobacion_ua): {titulo2.uuid}")
    else:
        titulo_uuid2 = titulo2.uuid
        print(f"[INFO] Título ya existe (pendiente_aprobacion_ua): {titulo2.uuid}")
    titulos_creados.append(titulo2)
    
    # 3. Título en estado "Aprobado por UA" - para probar siguiente paso
    titulo_uuid3 = uuid.uuid4()
    estado3 = LifeCycleState.objects.get(name=TituloStates.aprobado_ua)
    
    titulo3, created3 = File.objects.get_or_create(
        titulo='Título de Prueba - Aprobado por UA',
        defaults={
            'uuid': titulo_uuid3,
            'estado': TituloStates.aprobado_ua,
            'doctype_obj': doctype,
            'life_cycle_state_obj': estado3,
            'serie': serie2,
            'doctype_legacy': 'títulos',
            'life_cycle_state_legacy': TituloStates.aprobado_ua,
            'filename': '8205855_titulo.pdf'
        }
    )
    if created3:
        titulo3.set_metadata('metadata.titulo_dni', '8205855')
        titulo3.set_metadata('metadata.titulo_carrera', 'Medicina')
        titulo3.set_metadata('metadata.titulo_titulo', 'Médico')
        print(f"[OK] Título creado (aprobado_ua): {titulo3.uuid}")
    else:
        titulo_uuid3 = titulo3.uuid
        print(f"[INFO] Título ya existe (aprobado_ua): {titulo3.uuid}")
    titulos_creados.append(titulo3)
    
    # 4. Título en estado "Pendiente Blockchain" - para probar callback blockchain
    titulo_uuid4 = uuid.uuid4()
    estado4 = LifeCycleState.objects.get(name=TituloStates.pendiente_blockchain)
    
    titulo4, created4 = File.objects.get_or_create(
        titulo='Título de Prueba - Pendiente Blockchain',
        defaults={
            'uuid': titulo_uuid4,
            'estado': TituloStates.pendiente_blockchain,
            'doctype_obj': doctype,
            'life_cycle_state_obj': estado4,
            'serie': serie2,
            'doctype_legacy': 'títulos',
            'life_cycle_state_legacy': TituloStates.pendiente_blockchain,
            'filename': '8205856_titulo.pdf'
        }
    )
    if created4:
        titulo4.set_metadata('metadata.titulo_dni', '8205856')
        titulo4.set_metadata('metadata.titulo_carrera', 'Contador')
        titulo4.set_metadata('metadata.titulo_titulo', 'Contador Público')
        titulo4.set_feature('registro.en.blockchain', 'pending')
        print(f"[OK] Título creado (pendiente_blockchain): {titulo4.uuid}")
    else:
        titulo_uuid4 = titulo4.uuid
        print(f"[INFO] Título ya existe (pendiente_blockchain): {titulo4.uuid}")
    titulos_creados.append(titulo4)
    
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total de títulos disponibles: {len(titulos_creados)}")
    for titulo in titulos_creados:
        print(f"  - {titulo.titulo}")
        print(f"    UUID: {titulo.uuid}")
        print(f"    Estado: {titulo.life_cycle_state.name}")
        print(f"    Serie: {titulo.serie.name if titulo.serie else 'N/A'}")
        print()
    
    return titulos_creados

if __name__ == "__main__":
    crear_titulos_prueba()

