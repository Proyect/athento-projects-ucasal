#!/usr/bin/env python
"""
Script para crear actas de prueba para testing
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from endpoints.actas.models import Acta
from model.File import File, Doctype, LifeCycleState, Team
from ucasal.utils import ActaStates
import uuid

def crear_actas_prueba():
    """Crear actas de prueba en diferentes estados"""
    
    print("=" * 70)
    print("CREANDO ACTAS DE PRUEBA")
    print("=" * 70)
    
    # Asegurar que existan los datos base
    team, _ = Team.objects.get_or_create(name='UCASAL', defaults={'label': 'UCASAL'})
    doctype, _ = Doctype.objects.get_or_create(name='acta', defaults={'label': 'Acta de Examen'})
    
    actas_creadas = []
    
    # 1. Acta en estado "recibida" - para probar envío de OTP
    acta_uuid1 = uuid.uuid4()
    acta1, created1 = Acta.objects.get_or_create(
        titulo="Acta de Prueba - Recibida",
        defaults={
            'uuid': acta_uuid1,
            'descripcion': 'Acta creada para probar envío de OTP',
            'docente_asignado': 'profesor1@test.com',
            'nombre_docente': 'Prof. Test 1',
            'codigo_sector': '001',
            'estado': 'recibida'
        }
    )
    if created1:
        print(f"[OK] Acta creada (recibida): {acta1.uuid}")
    else:
        acta_uuid1 = acta1.uuid
        print(f"[INFO] Acta ya existe (recibida): {acta1.uuid}")
    
    # Crear File correspondiente
    lifecycle_state1, _ = LifeCycleState.objects.get_or_create(name=ActaStates.recibida)
    file1, file_created1 = File.objects.get_or_create(
        uuid=acta_uuid1,
        defaults={
            'titulo': acta1.titulo,
            'estado': ActaStates.recibida,
            'doctype_obj': doctype,
            'life_cycle_state_obj': lifecycle_state1,
            'doctype_legacy': 'acta',
            'life_cycle_state_legacy': ActaStates.recibida
        }
    )
    if file_created1:
        file1.set_metadata('metadata.acta_docente_asignado', acta1.docente_asignado)
        file1.set_metadata('metadata.acta_nombre_docente_asignado', acta1.nombre_docente)
        print(f"[OK] File creado para acta recibida: {file1.uuid}")
    actas_creadas.append(acta1)
    
    # 2. Acta en estado "pendiente_otp" - para probar registro de OTP
    acta_uuid2 = uuid.uuid4()
    acta2, created2 = Acta.objects.get_or_create(
        titulo="Acta de Prueba - Pendiente OTP",
        defaults={
            'uuid': acta_uuid2,
            'descripcion': 'Acta creada para probar registro de OTP',
            'docente_asignado': 'profesor2@test.com',
            'nombre_docente': 'Prof. Test 2',
            'codigo_sector': '002',
            'estado': 'pendiente_otp'
        }
    )
    if created2:
        print(f"[OK] Acta creada (pendiente_otp): {acta2.uuid}")
    else:
        acta_uuid2 = acta2.uuid
        print(f"[INFO] Acta ya existe (pendiente_otp): {acta2.uuid}")
    
    # Crear File correspondiente
    lifecycle_state2, _ = LifeCycleState.objects.get_or_create(name=ActaStates.pendiente_otp)
    file2, file_created2 = File.objects.get_or_create(
        uuid=acta_uuid2,
        defaults={
            'titulo': acta2.titulo,
            'estado': ActaStates.pendiente_otp,
            'doctype_obj': doctype,
            'life_cycle_state_obj': lifecycle_state2,
            'doctype_legacy': 'acta',
            'life_cycle_state_legacy': ActaStates.pendiente_otp
        }
    )
    if file_created2:
        file2.set_metadata('metadata.acta_docente_asignado', acta2.docente_asignado)
        file2.set_metadata('metadata.acta_nombre_docente_asignado', acta2.nombre_docente)
        print(f"[OK] File creado para acta pendiente_otp: {file2.uuid}")
    actas_creadas.append(acta2)
    
    # 3. Otra acta en "pendiente_otp" - para probar rechazo
    acta_uuid3 = uuid.uuid4()
    acta3, created3 = Acta.objects.get_or_create(
        titulo="Acta de Prueba - Pendiente OTP (Rechazo)",
        defaults={
            'uuid': acta_uuid3,
            'descripcion': 'Acta creada para probar rechazo',
            'docente_asignado': 'profesor3@test.com',
            'nombre_docente': 'Prof. Test 3',
            'codigo_sector': '003',
            'estado': 'pendiente_otp'
        }
    )
    if created3:
        print(f"[OK] Acta creada (pendiente_otp - rechazo): {acta3.uuid}")
    else:
        acta_uuid3 = acta3.uuid
        print(f"[INFO] Acta ya existe (pendiente_otp - rechazo): {acta3.uuid}")
    
    # Crear File correspondiente
    file3, file_created3 = File.objects.get_or_create(
        uuid=acta_uuid3,
        defaults={
            'titulo': acta3.titulo,
            'estado': ActaStates.pendiente_otp,
            'doctype_obj': doctype,
            'life_cycle_state_obj': lifecycle_state2,  # mismo estado
            'doctype_legacy': 'acta',
            'life_cycle_state_legacy': ActaStates.pendiente_otp
        }
    )
    if file_created3:
        file3.set_metadata('metadata.acta_docente_asignado', acta3.docente_asignado)
        file3.set_metadata('metadata.acta_nombre_docente_asignado', acta3.nombre_docente)
        print(f"[OK] File creado para acta pendiente_otp (rechazo): {file3.uuid}")
    actas_creadas.append(acta3)
    
    # 4. Acta en estado "pendiente_blockchain" - para probar callback
    acta_uuid4 = uuid.uuid4()
    acta4, created4 = Acta.objects.get_or_create(
        titulo="Acta de Prueba - Pendiente Blockchain",
        defaults={
            'uuid': acta_uuid4,
            'descripcion': 'Acta creada para probar callback blockchain',
            'docente_asignado': 'profesor4@test.com',
            'nombre_docente': 'Prof. Test 4',
            'codigo_sector': '004',
            'estado': 'pendiente_blockchain',
            'firmada_con_otp': True,
            'hash_documento': 'test_hash_' + str(uuid.uuid4())[:32]
        }
    )
    if created4:
        print(f"[OK] Acta creada (pendiente_blockchain): {acta4.uuid}")
    else:
        acta_uuid4 = acta4.uuid
        print(f"[INFO] Acta ya existe (pendiente_blockchain): {acta4.uuid}")
    
    # Crear File correspondiente
    lifecycle_state4, _ = LifeCycleState.objects.get_or_create(name=ActaStates.pendiente_blockchain)
    file4, file_created4 = File.objects.get_or_create(
        uuid=acta_uuid4,
        defaults={
            'titulo': acta4.titulo,
            'estado': ActaStates.pendiente_blockchain,
            'doctype_obj': doctype,
            'life_cycle_state_obj': lifecycle_state4,
            'doctype_legacy': 'acta',
            'life_cycle_state_legacy': ActaStates.pendiente_blockchain
        }
    )
    if file_created4:
        file4.set_metadata('metadata.acta_docente_asignado', acta4.docente_asignado)
        file4.set_metadata('metadata.acta_nombre_docente_asignado', acta4.nombre_docente)
        print(f"[OK] File creado para acta pendiente_blockchain: {file4.uuid}")
    actas_creadas.append(acta4)
    
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total de actas disponibles: {len(actas_creadas)}")
    for acta in actas_creadas:
        print(f"  - {acta.titulo}")
        print(f"    UUID: {acta.uuid}")
        print(f"    Estado: {acta.estado}")
        print(f"    Docente: {acta.docente_asignado}")
        print()
    
    return actas_creadas

if __name__ == "__main__":
    crear_actas_prueba()

