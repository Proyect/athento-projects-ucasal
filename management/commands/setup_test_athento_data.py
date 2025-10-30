# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from model.File import Doctype, LifeCycleState, Team, Serie
from ucasal.utils import TituloStates, ActaStates


class Command(BaseCommand):
    help = 'Crea datos de prueba para testing sin Athento (Teams, Doctypes, States, Series)'
    
    def handle(self, *args, **options):
        self.stdout.write("[*] Configurando datos mock de Athento...")
        
        # 1. Crear Team UCASAL
        team, created = Team.objects.get_or_create(
            name='UCASAL',
            defaults={'label': 'UCASAL'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'[OK] Team creado: {team.name}'))
        else:
            self.stdout.write(f'   Team ya existe: {team.name}')
        
        # 2. Crear Doctypes
        doctypes = [
            {'name': 'acta', 'label': 'Acta de Examen'},
            {'name': 'títulos', 'label': 'Títulos Universitarios'},
        ]
        
        for dt_data in doctypes:
            doctype, created = Doctype.objects.get_or_create(
                name=dt_data['name'],
                defaults={'label': dt_data['label']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'[OK] Doctype creado: {doctype.name}'))
            else:
                self.stdout.write(f'   Doctype ya existe: {doctype.name}')
        
        # 3. Crear Estados del Ciclo de Vida para Actas
        estados_actas = [
            {'name': ActaStates.recibida, 'maximum_time': None},
            {'name': ActaStates.pendiente_otp, 'maximum_time': 4320},  # 3 días
            {'name': ActaStates.pendiente_blockchain, 'maximum_time': 60},
            {'name': ActaStates.firmada, 'maximum_time': None},
            {'name': ActaStates.fallo_blockchain, 'maximum_time': None},
            {'name': ActaStates.rechazada, 'maximum_time': None},
        ]
        
        self.stdout.write("\n[*] Creando estados para Actas...")
        for estado_data in estados_actas:
            estado, created = LifeCycleState.objects.get_or_create(
                name=estado_data['name'],
                defaults={'maximum_time': estado_data.get('maximum_time')}
            )
            if created:
                self.stdout.write(f'   [OK] Estado creado: {estado.name}')
        
        # 4. Crear Estados del Ciclo de Vida para Títulos
        estados_titulos = [
            {'name': TituloStates.recibido, 'maximum_time': None},
            {'name': TituloStates.pendiente_aprobacion_ua, 'maximum_time': 4320},  # 3 días
            {'name': TituloStates.aprobado_ua, 'maximum_time': None},
            {'name': TituloStates.pendiente_aprobacion_r, 'maximum_time': 4320},  # 3 días
            {'name': TituloStates.aprobado_r, 'maximum_time': None},
            {'name': TituloStates.pendiente_firma_sg, 'maximum_time': 2880},  # 2 días
            {'name': TituloStates.firmado_sg, 'maximum_time': None},
            {'name': TituloStates.pendiente_blockchain, 'maximum_time': 60},
            {'name': TituloStates.registrado_blockchain, 'maximum_time': None},
            {'name': TituloStates.titulo_emitido, 'maximum_time': None},
            {'name': TituloStates.rechazado, 'maximum_time': None},
        ]
        
        self.stdout.write("\n[*] Creando estados para Títulos...")
        for estado_data in estados_titulos:
            estado, created = LifeCycleState.objects.get_or_create(
                name=estado_data['name'],
                defaults={'maximum_time': estado_data.get('maximum_time')}
            )
            if created:
                self.stdout.write(f'   [OK] Estado creado: {estado.name}')
        
        # 5. Crear Series para Actas
        series_actas = [
            'actas_nuevas',
            'actas_revisadas',
        ]
        
        # También crear series por sector (001_, 002_, etc.) si es necesario
        # Para simplificar, solo creamos las principales
        
        self.stdout.write("\n[*] Creando series para Actas...")
        for serie_name in series_actas:
            serie, created = Serie.objects.get_or_create(
                name=serie_name,
                defaults={
                    'label': serie_name.replace('_', ' ').title(),
                    'team': team
                }
            )
            if created:
                self.stdout.write(f'   [OK] Serie creada: {serie.name}')
            else:
                self.stdout.write(f'   Serie ya existe: {serie.name}')
        
        # 6. Crear Series para Títulos
        series_titulos = [
            'títulos',
            'títulos_pendiente_ua',
            'títulos_pendiente_rector',
            'títulos_pendiente_sg',
            'títulos_emitidos',
            'títulos_rechazados',
        ]
        
        self.stdout.write("\n[*] Creando series para Títulos...")
        for serie_name in series_titulos:
            serie, created = Serie.objects.get_or_create(
                name=serie_name,
                defaults={
                    'label': serie_name.replace('_', ' ').title(),
                    'team': team
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'   [OK] Serie creada: {serie.name}'))
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("[OK] Datos de prueba creados exitosamente"))
        self.stdout.write("="*50)
        
        # Resumen
        self.stdout.write(f"\n[*] Resumen:")
        self.stdout.write(f"   Teams: {Team.objects.count()}")
        self.stdout.write(f"   Doctypes: {Doctype.objects.count()}")
        self.stdout.write(f"   Estados: {LifeCycleState.objects.count()}")
        self.stdout.write(f"   Series: {Serie.objects.count()}")
        
        self.stdout.write("\n[INFO] Ahora puedes probar los endpoints y operations sin Athento")
