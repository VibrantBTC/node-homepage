# Use a small Python image
FROM python:3.11-slim

# System packages needed for Pillow (QR) and SSL sockets
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps
RUN pip install --no-cache-dir \
    Flask==3.0.0 \
    requests==2.32.3 \
    PyYAML==6.0.2 \
    qrcode[pil]==7.4.2

# Copy app
WORKDIR /app
COPY app/ /app/

# Static files are already in /app/static
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default port (override by APP_PORT)
ENV APP_PORT=8088

EXPOSE 8088

CMD ["python", "server.py"]
