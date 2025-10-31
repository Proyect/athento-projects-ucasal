"""
Clase base para operaciones de documentos
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
try:
    from sp_logger import SpLogger
except ImportError:
    from ucasal.mocks.sp_logger import SpLogger


class DocumentOperation(ABC):
    """
    Clase base abstracta para operaciones que trabajan con documentos
    """
    version: str = "1.0"
    name: str = ""
    description: str = ""
    configuration_parameters: Dict[str, Any] = {}
    
    def __init__(self, document=None, **params):
        """
        Inicializa la operation con un documento y parámetros adicionales
        
        Args:
            document: El documento (File) sobre el que operar
            **params: Parámetros adicionales de configuración
        """
        self.document = document
        self.params = params
        self._logger = SpLogger("athentose", self.__class__.__name__)
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta la operación
        
        Returns:
            Dict con el resultado de la operación:
            {
                'msg_type': 'success'|'error'|'info',
                'msg': 'Mensaje descriptivo'
            }
        """
        pass
    
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Método que ejecuta la operación (wrapper para execute)
        
        Returns:
            Dict con el resultado de la operación
        """
        try:
            return self.execute(*args, **kwargs)
        except Exception as e:
            self._logger.error(f"Error en {self.__class__.__name__}: {str(e)}", exc_info=True)
            return {
                'msg_type': 'error',
                'msg': f'Error ejecutando operación: {str(e)}'
            }

