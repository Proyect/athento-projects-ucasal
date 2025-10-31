"""
Sistema de autenticación personalizado
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth.models import AnonymousUser


class CustomJWTAuthentication(JWTAuthentication):
    """
    Autenticación JWT personalizada que maneja errores de forma más amigable
    """
    
    def authenticate(self, request):
        """
        Autentica el request usando JWT
        
        Returns:
            tuple: (user, token) si autenticado, None si no requiere autenticación
        """
        header = self.get_header(request)
        if header is None:
            return None
        
        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None
        
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        
        return (user, validated_token)

