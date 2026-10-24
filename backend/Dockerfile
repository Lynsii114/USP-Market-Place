FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Shell expansion is required for Railway's injected PORT.
# No migrations, schema creation, or seed commands run here.
CMD ["sh", "-c", "exec gunicorn usp_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
