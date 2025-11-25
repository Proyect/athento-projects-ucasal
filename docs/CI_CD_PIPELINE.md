# CI/CD Pipeline - Proyecto UCASAL

## Resumen

Este documento describe la configuración del pipeline de CI/CD para el proyecto UCASAL usando GitHub Actions.

**Fecha**: 2025-01-31  
**Estado**: ✅ Implementado

---

## 1. Configuración del Pipeline

### 1.1 Archivo de Configuración

El pipeline está configurado en `.github/workflows/ci.yml` y se ejecuta automáticamente en:

- **Push** a ramas `main` o `develop`
- **Pull Requests** hacia `main` o `develop`

### 1.2 Jobs del Pipeline

El pipeline incluye 4 jobs principales:

1. **test**: Ejecuta tests y verificaciones
2. **lint**: Verifica calidad de código
3. **security**: Escanea vulnerabilidades
4. **build**: Construye imagen Docker (solo en main)

---

## 2. Job: Test

### 2.1 Servicios

- **PostgreSQL 15**: Base de datos para tests
- **Redis 7**: Cache para tests

### 2.2 Pasos

1. **Checkout**: Obtiene el código
2. **Setup Python**: Configura Python 3.11
3. **Cache**: Cachea paquetes pip
4. **Install dependencies**: Instala requirements.txt
5. **Run migrations**: Ejecuta migraciones de Django
6. **Run tests**: Ejecuta todos los tests con verbosidad 2

### 2.3 Variables de Entorno

```yaml
DATABASE_ENGINE: django.db.backends.postgresql
DATABASE_NAME: ucasal_test
DATABASE_USER: ucasal
DATABASE_PASSWORD: ucasal
DATABASE_HOST: localhost
DATABASE_PORT: 5432
REDIS_URL: redis://localhost:6379/1
DJANGO_SECRET_KEY: test-secret-key-for-ci
DJANGO_DEBUG: 'False'
```

---

## 3. Job: Lint

### 3.1 Herramientas

- **flake8**: Linting de Python
- **black**: Formateo de código
- **isort**: Ordenamiento de imports
- **pylint**: Análisis estático (opcional)

### 3.2 Verificaciones

1. **flake8**: Verifica errores críticos y complejidad
2. **black**: Verifica formato de código (no modifica)
3. **isort**: Verifica orden de imports (no modifica)
4. **pylint**: Análisis estático básico

---

## 4. Job: Security

### 4.1 Herramientas

- **bandit**: Escaneo de seguridad de código Python
- **safety**: Verificación de vulnerabilidades en dependencias

### 4.2 Escaneos

1. **Bandit**: Busca vulnerabilidades comunes en código Python
2. **Safety**: Verifica dependencias conocidas con vulnerabilidades

---

## 5. Job: Build

### 5.1 Condiciones

- Solo se ejecuta en push a `main`
- Requiere que `test` y `lint` pasen

### 5.2 Pasos

1. **Checkout**: Obtiene el código
2. **Setup Docker Buildx**: Configura Docker para build
3. **Build Docker image**: Construye imagen Docker con cache

---

## 6. Uso Local

### 6.1 Ejecutar Tests Localmente

```bash
# Con PostgreSQL
export DATABASE_ENGINE=django.db.backends.postgresql
export DATABASE_NAME=ucasal_test
export DATABASE_USER=ucasal
export DATABASE_PASSWORD=ucasal
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export REDIS_URL=redis://localhost:6379/1

python manage.py test --verbosity=2
```

### 6.2 Ejecutar Linting Localmente

```bash
# Instalar herramientas
pip install flake8 black isort pylint

# Ejecutar flake8
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Verificar formato
black --check .
isort --check-only .

# Ejecutar pylint
pylint --disable=all --enable=E,F,W,R,C --max-line-length=127 endpoints/ core/ model/
```

### 6.3 Ejecutar Security Scan Localmente

```bash
# Instalar herramientas
pip install bandit safety

# Ejecutar bandit
bandit -r .

# Verificar dependencias
safety check
```

---

## 7. Configuración de Badges

Puedes agregar badges al README para mostrar el estado del pipeline:

```markdown
![CI](https://github.com/tu-usuario/athento-projects-ucasal/workflows/CI%2FCD%20Pipeline/badge.svg)
```

---

## 8. Mejoras Futuras

### 8.1 Coverage

Agregar reporte de cobertura de tests:

```yaml
- name: Generate coverage report
  run: |
    pip install coverage
    coverage run --source='.' manage.py test
    coverage report
    coverage xml
```

### 8.2 Deploy Automático

Agregar job de deploy para producción:

```yaml
deploy:
  needs: [test, lint, security, build]
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main'
  steps:
    - name: Deploy to production
      # Configurar deploy según infraestructura
```

### 8.3 Notificaciones

Agregar notificaciones en caso de fallos:

```yaml
- name: Notify on failure
  if: failure()
  uses: actions/github-script@v6
  with:
    script: |
      # Enviar notificación (email, Slack, etc.)
```

---

## 9. Troubleshooting

### 9.1 Tests Fallan

- Verificar que PostgreSQL y Redis estén corriendo
- Verificar variables de entorno
- Revisar logs de GitHub Actions

### 9.2 Linting Fallan

- Ejecutar `black .` para formatear código
- Ejecutar `isort .` para ordenar imports
- Corregir errores de flake8 manualmente

### 9.3 Security Scan Encuentra Problemas

- Revisar reportes de bandit y safety
- Actualizar dependencias vulnerables
- Corregir código con vulnerabilidades

---

**Última actualización**: 2025-01-31  
**Versión**: 1.0.0  
**Estado**: ✅ Implementado



