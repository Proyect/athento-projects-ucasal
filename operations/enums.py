"""
Enumeraciones para operations
"""
from enum import Enum


class ProcessOperationParameterType(Enum):
    """Tipos de parámetros para operations"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    FILE = "file"
    SELECT = "select"


class ProcessOperationParameterChoiceType(Enum):
    """Tipos de elección para parámetros"""
    SINGLE = "single"
    MULTIPLE = "multiple"

