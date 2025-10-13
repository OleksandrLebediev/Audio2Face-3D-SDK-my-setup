# 🚀 Быстрое развертывание Audio2X SDK

## Минимальные шаги для запуска на сервере

### 📋 Предварительные требования

1. **Сервер** с Ubuntu 20.04+ и NVIDIA GPU (CUDA 12.8+)
2. **SSH доступ** к серверу
3. **Hugging Face токен** с доступом к gated моделям

### 🔑 Получение Hugging Face токена

1. Регистрация на https://huggingface.co
2. Создание токена: https://huggingface.co/settings/tokens
   - Выберите "Read access to contents of all public gated repos you can access"
3. Принятие лицензии: https://huggingface.co/nvidia/Audio2Emotion-v2.2
   - Нажмите "Agree and access repository"

---

## ⚡ Способ 1: Автоматический деплой (один скрипт)

```bash
# На вашем локальном компьютере
cd Audio2Face-3D-SDK/deployment
chmod +x deploy.sh
./deploy.sh ubuntu@YOUR_SERVER_IP YOUR_HF_TOKEN
```

**Готово!** Сервис будет доступен на `http://YOUR_SERVER_IP:8000`

---

## 🐳 Способ 2: Docker Compose (2 команды)

### На сервере:

```bash
# 1. Клонирование и настройка
git clone https://github.com/NVIDIA/Audio2Face-3D-SDK.git
cd Audio2Face-3D-SDK
git lfs pull

# 2. Создание .env файла
cat > .env << EOF
BUILD_TYPE=release
HF_TOKEN=YOUR_HUGGINGFACE_TOKEN_HERE
DOWNLOAD_MODELS=1
SERVER_PORT=8000
CUDA_PATH=/usr/local/cuda
TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu
EOF

# 3. Запуск
docker compose up -d

# 4. Просмотр логов
docker compose logs -f
```

---

## 🧪 Проверка работы

### Health Check
```bash
curl http://YOUR_SERVER_IP:8000/health
```

Ожидаемый результат:
```json
{
  "status": "ok",
  "build_type": "release",
  "cuda_path": "/usr/local/cuda",
  "tensorrt_root": "/usr/lib/x86_64-linux-gnu"
}
```

### Тест Inference (Эмоции)
```bash
curl -X POST http://YOUR_SERVER_IP:8000/infer/emotions \
  -F "audio=@sample-data/audio_1sec_16k_s16le.wav"
```

### Тест Inference (Blendshapes)
```bash
curl -X POST http://YOUR_SERVER_IP:8000/infer/blendshapes \
  -F "audio=@sample-data/audio_4sec_16k_s16le.wav"
```

---

## 🔧 Управление сервисом

### Docker Compose команды

```bash
# Просмотр логов
docker compose logs -f

# Перезапуск
docker compose restart

# Остановка
docker compose down

# Обновление и перезапуск
git pull && docker compose up -d --build

# Проверка статуса
docker compose ps
```

### Мониторинг GPU

```bash
# Однократная проверка
nvidia-smi

# Постоянный мониторинг
watch -n 1 nvidia-smi
```

---

## 🌐 Доступ извне (открытие портов)

### Настройка файрвола

```bash
# UFW (Ubuntu)
sudo ufw allow 8000/tcp
sudo ufw status

# firewalld (CentOS/RHEL)
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

### Настройка облачного провайдера

- **AWS**: Security Groups → Inbound Rules → Add port 8000
- **Google Cloud**: VPC firewall rules → Create rule → port 8000
- **Azure**: Network Security Group → Inbound security rules → port 8000

---

## 🔒 Продакшен настройки (опционально)

### 1. NGINX Reverse Proxy

```bash
# Раскомментируйте nginx секцию в docker-compose.yml
docker compose up -d
```

### 2. SSL сертификат (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. Ограничение ресурсов

Отредактируйте `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 16G
```

---

## ❗ Частые проблемы

### GPU не обнаружен в Docker

```bash
# Установка NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Тест
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

### Ошибка при загрузке моделей

```bash
# Проверьте, что вы приняли лицензию на HuggingFace
# https://huggingface.co/nvidia/Audio2Emotion-v2.2

# Перезапустите с правильным токеном
nano .env  # исправьте HF_TOKEN
docker compose restart
```

### Out of Memory

```bash
# Проверьте использование памяти
nvidia-smi

# Используйте менее требовательную конфигурацию
# или GPU с большей памятью (рекомендуется 8GB+)
```

---

## 📚 Дополнительная документация

- [Полная инструкция по деплою](../DEPLOYMENT.md)
- [Deployment файлы](README.md)
- [Основной README](../README.md)

---

## 💬 Поддержка

- **Issues**: https://github.com/NVIDIA/Audio2Face-3D-SDK/issues
- **Discussions**: https://github.com/NVIDIA/Audio2Face-3D-SDK/discussions

---

**Время развертывания**: 5-10 минут (автоматический скрипт) или 15-20 минут (ручная настройка)

