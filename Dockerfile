FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . /app/

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/media /app/tmp /app/staticfiles

# Configurar variables de entorno
ENV DJANGO_SETTINGS_MODULE=ucasal.docker_settings

# Exponer puerto
EXPOSE 8010

# Comando por defecto
CMD ["gunicorn", "ucasal.wsgi:application", "-b", "0.0.0.0:8010", "--workers", "3", "--timeout", "120"]
