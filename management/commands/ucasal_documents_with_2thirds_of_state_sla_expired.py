# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from datetime import datetime
from core.exceptions import AthentoseError
import importlib
from ucasal.utils import dumper, encodeJSON, decodeJSON

class Command(BaseCommand):
    help = "Runs custom operations once 2/3 of state SLA (or max_minutes) fot the speciefied life cycle state have elapsed."
    _logger = None
    def add_arguments(self, parser):
        parser.add_argument('--doctype_name', type=str, help="Doctypes to filter by")
        parser.add_argument('--excluded_series', type=str, default='', help="Exclude files from these series (comma separatd name list)")
        parser.add_argument('--state_name', type=str, help="Lifecycle state")
        parser.add_argument('--max_minutes', type=str, default='sla', help="Override sla minutes with this value: 'sla' for no overriding, or a positive integer")
        parser.add_argument('--run_op_after_max_minutes', type=str, default="1", help="'0' if op_name should NOT run after max_minutes has been exceeded, or any other value otherwise.")
        parser.add_argument('--op_name', type=str, help="Name of the peration to run on the matching files")
        parser.add_argument('--op_params', type=str, default='', help="Parameters for the operation")

    def handle(self, *args, **options):
        from file.models import File
        from django.contrib.auth.models import User
        from doctypes.models import DocumentType
        from series.models import Serie
        from ucasal.utils import automation_user
        import math
        from sp_logger import SpLogger

        logger = SpLogger("athentose", "cmd.2thirdsOfSla")
        self._logger = logger

        logger.entry(additional_info=options)

        #TODO: obtener 'excluded_serie_names', 'doctype_name', 'life_cycle_state_name' y 'max_minutes' por parámetros
        doctype_name = options['doctype_name']  #'acta'
        life_cycle_state_name = options['state_name'] #'Pendiente Firma OTP'
        max_minutes = options.get('max_minutes', 'sla') #0 
        excluded_serie_names = options.get('excluded_series', '') #'actas_nuevas,actas_revisadas'
        #TODO: validar estos dos parámetros
        op_name = options['op_name'] 
        op_params = decodeJSON(options['op_params'].replace("'", '"'))

        # Validate max_minutes
        max_minutes = int(max_minutes) if str(max_minutes).isdigit() else max_minutes
        if max_minutes!='sla' and (not isinstance(max_minutes, int) or max_minutes <= 0) :
            raise AthentoseError("'max_minutes' must be 'sla' or int >0 insteaf of '%s'" % str(max_minutes))
        
        max_minutes = None if max_minutes == 'sla' else max_minutes

        # Get run_op_after_max_minutes
        run_op_after_max_minutes = True if options.get('run_op_after_max_minutes') == '1' else False
        
        # Filter documents by doctype_name, life_cycle_state_name and excluded_serie_names
        excluded_series_uuids = self._get_series_uuids(excluded_serie_names)
        
        userAdmin = User.objects.get(username=automation_user)
        doctype = DocumentType.objects.get(name=doctype_name)
        doctype_uuid = str(doctype.uuid)


        filter_state_uuid = str(doctype.current_life_cycle.states.get(name=life_cycle_state_name).uuid)

        filters = {
        	"AND": [
        		{"type": "serie", "schema": {"value": excluded_series_uuids},  "negate": True},
        		{"type": "doctype", "schema": {"value": [doctype_uuid]}},
        		{"type": "lifecycle_state", "schema": {"value": [filter_state_uuid]}},
            ]
        }

        print(f"filters:\r\n{filters}")
        logger.debug(f"filters:\r\n{filters}")

        fils = File.objects.advanced_search(userAdmin, filters=filters)

        print(f"len(fils): {len(fils)}")
        logger.debug(f"len(fils) matching 'filters': {len(fils)}")

        # Filter files that have a state SLA and a remaining time to expiration 
        # > 0 and < 2/3 of maximum_time
        print('Filering files about to expire...')
        logger.debug('Filering files about to expire...')
        fils = [f for f in fils if self._should_run_operation(f, max_minutes, run_op_after_max_minutes)]
        print(f"len(fils) about to expire: {len(fils)}")
        logger.debug(f"len(fils) about to expire: {len(fils)}")


        # Run operations on matching files
        print('Processing %s files about to expire...' % len(fils))
        logger.debug('Processing %s files about to expire...' % len(fils))
        for fil in fils:
            #TODO: descartar las que tienen 1 en el feature state_sla_nearly_expired_notified[<state name>]
            logger.debug(f"  File '{fil.doctype.label}' in '{fil.serie.team.label}': {fil.get_url_file_view()}")
            logger.debug(f"  State: {fil.life_cycle_state.name}. SLA: {fil.life_cycle_state.maximum_time}. State date: {fil.life_cycle_state_date}")
            
            # Execute specified operations for matching files
            #ucasal_handle_2thirds_of_state_sla_expired
            operation  = importlib.import_module(op_name)
            logger.debug('Running operation "' + op_name + '"  with these params:\r\n' + encodeJSON(op_params, default=dumper, indent=2) )
            operation.run(str(fil.uuid), **op_params)                
            #TODO; no funciona la ejecución por categorías
            #fil.run_operations_by_category('life_cycle_state_sla_nearly_expired')
            
            #TODO: setear 1 en el feature  state_sla_nearly_expired_notified[<state name>]
        

        print(f'{len(fils)} file(s) with state sla nearly expired where processed.')
        logger.debug(f'{len(fils)} file(s) with state sla nearly expired where processed.')
        print('Command action_on_documents_with_2thirds_of_sla_expired - EXIT')

        logger.exit()

    def handle_backup(self, *args, **options):
        from file.models import File
        from lifecycle.models import State

        logger = self._logger
        logger.entry()
        
        states = State.objects.filter(maximum_time__isnull=False)
        states = states.filter(run_operations_sla_expired=False) # or True??
        processed_files = 0
        for state in states:
            logger.debug(f" Processing state {state.name} ({state.uuid})")
            logger.debug(f" SLA minutes: {state.maximum_time}")
            
            fils = File.objects.filter(life_cycle_state=state)
            logger.debug(f" {len(fils)} file(s) in state '{state.name}.'")

            max_time = round(state.maximum_time * 2 / 3)
            fils = fils.life_cycle_changed_more_than_x_minutes(max_time)
            logger.debug(f" {len(fils)} with state sla nearly expired.")

            processed_files += len(fils)
            for fil in fils:
                logger.debug(f"  File '{fil.doctype.label} in {fil.serie.team.label}': {fil.get_url_file_view()}")
                logger.debug(f"  State: {fil.life_cycle_state.name}. SLA: {fil.life_cycle_state.maximum_time}. State date: {fil.life_cycle_state_date}")
                
                #fil.run_operations_by_category('life_cycle_state_sla_nearly_expired')

        logger.debug(f'{processed_files} file(s) with state sla nearly expired where processed.')
        logger.exit()

    # Returns True if the file has a state SLA in its current state and the time
    # in the current state is > 2/3 of sla_max_minutes_override and < sla_max_minutes_override (or run_op_after_max_minutes == True)
    def _should_run_operation(self, fil, sla_max_minutes_override:int=None, run_op_after_max_minutes:bool=True )->bool:
        import math
        logger = self._logger

        logger.entry()

        print(f" Analizing file: {fil.get_url_file_view()}")
        logger.debug(f" Analizing file: {fil.get_url_file_view()}")        

       # Check if file has an SLA set in its current State
        sla_max_minutes = fil.life_cycle_state.maximum_time
        print(f" SLA in minutes: {sla_max_minutes}")
        logger.debug(f" SLA in minutes: {sla_max_minutes}")
        if not isinstance(sla_max_minutes, int):
          print(' State SLA not set. Returning with false')
          logger.debug(' State SLA not set. Returning with false')
          return False        

        # Override SLA time if sla_max_minutes_override != None
        max_minutes = sla_max_minutes_override if sla_max_minutes_override != None else sla_max_minutes 
        print(f" Calculated max_minutes: {max_minutes}")
        logger.debug(f" Calculated max_minutes: {max_minutes}")
       

        # Calculate elapsed time in current state
        current_state_date = fil.life_cycle_state_date
        now = datetime.now(current_state_date.tzinfo)
        elapsed_time = now - current_state_date
        elapsed_minutes = elapsed_time.total_seconds() / 60

        print(f" Elapsed minutes: {elapsed_minutes}")
        logger.debug(f" Elapsed minutes: {elapsed_minutes}")
        

        # Check if elapsed time is between  2/3 of SLA and max_minutes
        about_to_expire_theshold = max_minutes / 3 * 2
        print(f" About to expire threshold: {about_to_expire_theshold}")
        logger.debug(f" About to expire threshold: {about_to_expire_theshold}")

        is_about_to_expire = elapsed_minutes > about_to_expire_theshold and (elapsed_minutes < max_minutes or run_op_after_max_minutes == True)
        print(f" Is about to expire: {is_about_to_expire}")
        logger.debug(f" Is about to expire: {is_about_to_expire}")

        return logger.exit(is_about_to_expire)
    
    def _get_series_uuids(self, excluded_series_csl:str)->list:
        logger = self._logger
        logger.entry()

        excluded_series_csl = excluded_series_csl.strip()

        excluded_series_names = excluded_series_csl.split(',')
        excluded_series_uuids = [] if excluded_series_csl=='' else [self._get_serie_uuid(serie_name) for serie_name in excluded_series_names]
            
        return logger.exit(excluded_series_uuids)

    def _get_serie_uuid(self, excluded_serie_name:str)->str:
        from series.models import Serie
        logger = self._logger
        logger.entry()
        
        try:
            s = Serie.objects.get(name=excluded_serie_name.strip())

            return logger.exit(str(s.uuid))
        except  Serie.DoesNotExist:
            raise logger.exit(AthentoseError("Serie with name '%s' does not exist" % excluded_serie_name),exc_info=True)
