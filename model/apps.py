from django.apps import AppConfig

class ModelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'model'
    verbose_name = 'Model Package'
    
    def ready(self):
        """Importar admin cuando la app esté lista"""
        try:
            import model.admin  # noqa
        except ImportError:
            pass




