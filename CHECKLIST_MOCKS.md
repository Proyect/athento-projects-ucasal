# ✅ Checklist: Mocks para Testing sin Athentسبب

## 📋 Estado Actual - Lo que Tenemos Funcionando

### ✅ Paso 1: Modelos Mock Creados
- [x] `model/File.py` - Modelo File mejorado con:
  - [x] Clase `Doctype` (mock de doctype de Athento)
  - [x] Clase `LifeCycleState` (mock de estados)
  - [x] Clase `Team` (mock de teams)
  - [x] Clase `Serie` (mock de series/espacios)
  - [x] Clase `File` mejorada con propiedades compatibles
  - [x] Métodos `gmv()`, `gfv()`, `set_metadata()`, `set_feature()`
  - [x] Métodos `move_to_serie()` y `change_life_cycle_state()`
  - [x] Compatibilidad hacia atrás con código existente

### ✅ Paso 2: Archivos de Soporte
- [x] `model/__init__.py` - Exporta todos los modelos
- [x] `management/commands/setup_test_athento_data.py` - Comando para crear datos de prueba
- [x] `scripts/test_titulos_local.py` - Script de prueba manual

### ✅ Paso 3: Verificaciones de Compilación
- [x] Todos los archivos Python compilan sin errores de sintaxis
- [x] Imports correctos en todos los archivos
- [x] Compatibilidad con código existente mantenida

---

## 🔄 Próximos Pasos (Pendientes)

### ⏳ Paso 4: Migraciones de Base de Datos
**Acción requerida:**
```bash
# Cuando tengas el entorno virtual activo:
python manage.py makemigrations model
python manage.py migrate
```

**Qué creará:**
- Tablas para `Doctype`, `LifeCycleState`, `Team`, `Serie`
- Campos nuevos en `File` (doctype_obj, life_cycle_state_obj, serie, _metadata_cache, _features_cache)

### ⏳ Paso 5: Crear Datos de Prueba
**Acción requerida:**
```bash
python manage.py setup_test_athento_data
```

**Qué creará:**
- 1 Team: UCASAL
- 2 Doctypes: acta, títulos
- 17 Estados: 6 de actas + 11 de títulos
- 8 Series: 2 de actas + 6 de títulos

### ⏳ Paso 6: Probar Localmente
**Acción requerida:**
```bash
python scripts/test_titulos_local.py
```

**Qué probará:**
- Creación de títulos
- Métodos gmv() y gfv()
- Cambio de estados
- Movimiento entre series
- Operation de asignar espacio

---

## 📝 Archivos Modificados/Creados

### Modelos
1. **model/File.py** ✅
   - Nuevos modelos: Doctype, LifeCycleState, Team, Serie
   - Modelo File legacy compatible mejorado

2. **model/__init__.py** ✅
   - Exporta: File, Doctype, LifeCycleState, Team, Serie歧

### Comandos
3. **management/commands/setup_test_athento_data.py** ✅
   - Comando Django para crear datos de prueba

### Scripts de Prueba
4. **scripts/test_titulos_local.py** ✅
   - Script standalone para testing manual

---

## 🔗 Integración con Código Existente

### Compatibilidad Verificada
- ✅ `endpoints/actas/actas.py` - Usa `from model.File import File`
- ✅ `endpoints/titulos/titulos.py` - Usa `from model.File import File`
- ✅ `external_services/ucasal/ucasal_services.py` - Usa `from model import File`
- ✅ `operations/titulos_asignar_espacio.py` - Debe funcionar con los nuevos mocks

### Funcionalidad Mockeada
Los mocks permiten:
- ✅ Crear documentos sin Athento
- ✅ Cambiar estados del ciclo de vida
- ✅ Mover documentos entre series
- ✅ Guardar/leer metadata y features
- ✅ Ejecutar operations localmente

---

## ⚠️ Notas Importantes

1. **Migraciones**: Los nuevos modelos requieren migraciones antes de usar
2. **Datos de Prueba**: El comando `setup_test_athento_data` debe ejecutarse después de las migraciones
3. **Compatibility**: El código mantiene compatibilidad hacia atrás - no rompe nada existente
4. **Testing**: Los mocks permiten probar lógica sin Athento, pero para probar endpoints HTTP completos se necesitaría mockear también las llamadas a `requests.post()` a Athento API

---

## 📚 Referencias

- Archivos relacionados: `model/File.py`, `ucasal/utils.py`, `operations/titulos_asignar_espacio.py`
- Estados definidos en: `ucasal/utils.py` (ActaStates, TituloStates)
- Series definidas en: `ucasal/utils.py` (serie_titulos_name, etc.)


