# Model package
# Lazy imports - importar solo cuando se necesite para evitar problemas con Django setup

def __getattr__(name):
    """Lazy loading de modelos para evitar AppRegistryNotReady"""
    if name in ['File', 'Doctype', 'LifeCycleState', 'Team', 'Serie']:
        from .File import File, Doctype, LifeCycleState, Team, Serie
        globals()[name] = locals()[name]
        return locals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['File', 'Doctype', 'LifeCycleState', 'Team', 'Serie']
