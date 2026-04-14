FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для OpenCV и YOLO
# libgl1-mesa-glx заменен на libgl1 для новых версий Debian
RUN set -eux; \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    if apt-get -o Acquire::Retries=5 update; then \
        apt-get install -y \
            libgl1 \
            libglib2.0-0 \
            libsm6 \
            libxext6 \
            libxrender-dev \
            libgomp1 \
            || echo "WARNING: failed to install optional system libraries"; \
    else \
        echo "WARNING: apt mirrors are unavailable, continuing without optional system libraries"; \
    fi; \
    rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y opencv-python opencv-python-headless || true \
    && pip install --no-cache-dir --force-reinstall numpy==1.24.3 opencv-python-headless==4.8.1.78

# Копирование кода приложения
COPY . .

# Создание директории для моделей
RUN mkdir -p /app/models

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

