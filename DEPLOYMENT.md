# Развертывание Audio2X SDK на сервере

Это руководство объясняет, как развернуть Audio2X SDK на удаленном сервере через SSH с использованием Docker.

## Требования к серверу

### Минимальные требования:
- **ОС**: Ubuntu 20.04+ или другой Linux дистрибутив
- **GPU**: NVIDIA GPU с поддержкой CUDA 12.8.0+
- **RAM**: 8GB+
- **GPU Memory**: 4GB+
- **Хранилище**: 20GB+ свободного места
- **Docker**: 20.10+ с поддержкой NVIDIA Container Runtime

### Предварительная настройка сервера

1. **Установка Docker**:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

2. **Установка NVIDIA Container Toolkit**:
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

3. **Проверка GPU**:
```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

## Способ 1: Развертывание с помощью Docker Compose (Рекомендуется)

### 1. Подключение к серверу:
```bash
ssh user@your-server-ip
```

### 2. Клонирование репозитория:
```bash
git clone https://github.com/NVIDIA/Audio2Face-3D-SDK.git
cd Audio2Face-3D-SDK
git lfs pull
```

### 3. Настройка переменных окружения:
```bash
# Создайте файл .env
cat > .env << 'EOF'
# Build configuration
BUILD_TYPE=release
SKIP_BUILD=0

# CUDA and TensorRT paths (внутри контейнера)
CUDA_PATH=/usr/local/cuda
TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu

# Hugging Face token (для загрузки моделей)
HF_TOKEN=your_huggingface_token_here

# Опции запуска
DOWNLOAD_MODELS=1
RUN_UNIT_TESTS=0
BUILD_IN_CONTAINER=0

# Server settings
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
EOF
```

### 4. Получение Hugging Face токена:
```bash
# 1. Зарегистрируйтесь на https://huggingface.co
# 2. Перейдите на https://huggingface.co/settings/tokens
# 3. Создайте новый токен с правами "Read access to contents of all public gated repos you can access"
# 4. Примите лицензию на https://huggingface.co/nvidia/Audio2Emotion-v2.2
# 5. Добавьте токен в .env файл
```

### 5. Запуск сервиса:
```bash
# Используя docker-compose
docker compose up -d

# Просмотр логов
docker compose logs -f

# Остановка
docker compose down
```

## Способ 2: Ручное развертывание с Docker

### 1. Сборка образа:
```bash
docker build -t audio2x-sdk:latest .
```

### 2. Запуск контейнера:
```bash
docker run -d \
  --name audio2x-service \
  --gpus all \
  -p 8000:8000 \
  -e BUILD_TYPE=release \
  -e HF_TOKEN=your_huggingface_token \
  -e DOWNLOAD_MODELS=1 \
  -e CUDA_PATH=/usr/local/cuda \
  -e TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu \
  audio2x-sdk:latest \
  uvicorn server.app:app --host 0.0.0.0 --port 8000
```

## Способ 3: Развертывание как systemd service (без Docker)

Если вы хотите запустить сервис напрямую (не рекомендуется, но возможно):

### 1. Сборка проекта на сервере:
```bash
# Установите зависимости
sudo apt-get update
sudo apt-get install -y build-essential cmake ninja-build git git-lfs python3-venv

# Установите CUDA и TensorRT на хост
# (следуйте официальной документации NVIDIA)

# Соберите проект
./fetch_deps.sh release
export TENSORRT_ROOT_DIR="/path/to/tensorrt"
./build.sh all release

# Настройте Python окружение
python3 -m venv venv
source venv/bin/activate
pip install -r deps/requirements.txt -r requirements-service.txt

# Скачайте модели
hf auth login  # введите токен
./download_models.sh
./gen_testdata.sh
```

### 2. Создайте systemd service:
```bash
sudo nano /etc/systemd/system/audio2x.service
```

Используйте содержимое из файла `deployment/audio2x.service`.

### 3. Запустите сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl enable audio2x
sudo systemctl start audio2x
sudo systemctl status audio2x
```

## Проверка работы сервиса

### 1. Health check:
```bash
curl http://localhost:8000/health
```

### 2. Тест inference (эмоции):
```bash
curl -X POST http://localhost:8000/infer/emotions \
  -F "audio=@sample-data/audio_1sec_16k_s16le.wav"
```

### 3. Тест inference (blendshapes):
```bash
curl -X POST http://localhost:8000/infer/blendshapes \
  -F "audio=@sample-data/audio_4sec_16k_s16le.wav"
```

### 4. Открытие порта через файрвол (если нужно):
```bash
sudo ufw allow 8000/tcp
```

## Автоматический деплой со скриптом

Используйте скрипт `deployment/deploy.sh` для автоматизации:

```bash
# На вашем локальном компьютере
chmod +x deployment/deploy.sh
./deployment/deploy.sh user@your-server-ip /path/to/huggingface/token
```

## Мониторинг и обслуживание

### Просмотр логов (Docker Compose):
```bash
docker compose logs -f audio2x
```

### Перезапуск сервиса:
```bash
docker compose restart audio2x
```

### Обновление кода:
```bash
git pull
docker compose up -d --build
```

### Очистка:
```bash
docker compose down -v  # Удалить контейнеры и volumes
docker system prune -a  # Очистить неиспользуемые образы
```

## Производственная конфигурация

### Рекомендации для продакшена:

1. **Используйте NGINX как reverse proxy**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

2. **Настройте SSL с Let's Encrypt**:
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

3. **Добавьте ограничения ресурсов в docker-compose.yml**:
```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 16G
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

4. **Настройте логирование**:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "3"
```

## Troubleshooting

### Проблема: GPU не обнаружен в контейнере
```bash
# Проверьте nvidia-container-toolkit
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

### Проблема: Ошибка при загрузке моделей
```bash
# Убедитесь, что вы приняли лицензию на HuggingFace
# Проверьте правильность HF_TOKEN
```

### Проблема: Недостаточно GPU памяти
```bash
# Уменьшите batch size или используйте более мощный GPU
# Проверьте использование памяти: nvidia-smi
```

## Безопасность

1. **Не коммитьте .env файл с токенами**
2. **Используйте файрвол для ограничения доступа**
3. **Регулярно обновляйте Docker образы**
4. **Используйте HTTPS в продакшене**
5. **Ограничьте размер загружаемых файлов в NGINX**

## Контакты и поддержка

- GitHub Issues: https://github.com/NVIDIA/Audio2Face-3D-SDK/issues
- Documentation: [docs/README.md](docs/README.md)

