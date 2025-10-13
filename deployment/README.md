# Deployment Files

Эта папка содержит все необходимые файлы для развертывания Audio2X SDK на сервере.

## 📁 Файлы

### 1. `deploy.sh` - Автоматический скрипт развертывания
Основной скрипт для автоматической установки и настройки на удаленном сервере.

**Использование:**
```bash
chmod +x deploy.sh
./deploy.sh user@server-ip [huggingface_token]
```

**Пример:**
```bash
./deploy.sh ubuntu@192.168.1.100 hf_abc123xyz
```

**Что делает скрипт:**
- ✅ Проверяет SSH соединение
- ✅ Устанавливает Docker (если не установлен)
- ✅ Устанавливает NVIDIA Container Toolkit
- ✅ Клонирует/обновляет репозиторий
- ✅ Настраивает переменные окружения
- ✅ Собирает и запускает Docker контейнер
- ✅ Проверяет работоспособность сервиса

### 2. `audio2x.service` - Systemd service файл
Для запуска сервиса напрямую на сервере (без Docker).

**Установка:**
```bash
# На сервере
sudo cp audio2x.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable audio2x
sudo systemctl start audio2x
```

**Управление:**
```bash
sudo systemctl status audio2x   # Статус
sudo systemctl restart audio2x  # Перезапуск
sudo systemctl stop audio2x     # Остановка
journalctl -u audio2x -f        # Логи
```

### 3. `nginx.conf` - NGINX конфигурация
Reverse proxy для Audio2X сервиса с настройками безопасности.

**Использование:**
```bash
# Скопируйте в docker-compose.yml nginx секцию
# или используйте на хосте:
sudo cp nginx.conf /etc/nginx/sites-available/audio2x
sudo ln -s /etc/nginx/sites-available/audio2x /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. `env.example` - Пример переменных окружения
Шаблон для создания `.env` файла.

**Использование:**
```bash
cp env.example ../.env
nano ../.env  # Отредактируйте, добавьте HF_TOKEN
```

## 🚀 Быстрый старт

### Вариант 1: Автоматический деплой (рекомендуется)

```bash
# 1. Получите Hugging Face токен на https://huggingface.co/settings/tokens
# 2. Примите лицензию на https://huggingface.co/nvidia/Audio2Emotion-v2.2
# 3. Запустите скрипт деплоя
cd deployment
./deploy.sh user@your-server YOUR_HF_TOKEN
```

### Вариант 2: Ручной деплой с Docker Compose

```bash
# На сервере
git clone https://github.com/NVIDIA/Audio2Face-3D-SDK.git
cd Audio2Face-3D-SDK
cp deployment/env.example .env
nano .env  # Добавьте HF_TOKEN

docker compose up -d
docker compose logs -f
```

### Вариант 3: Деплой с systemd (без Docker)

```bash
# На сервере с CUDA и TensorRT
git clone https://github.com/NVIDIA/Audio2Face-3D-SDK.git
cd Audio2Face-3D-SDK

# Сборка
./fetch_deps.sh release
export TENSORRT_ROOT_DIR="/path/to/tensorrt"
./build.sh all release

# Python окружение
python3 -m venv venv
source venv/bin/activate
pip install -r deps/requirements.txt -r requirements-service.txt

# Модели
hf auth login
./download_models.sh
./gen_testdata.sh

# Systemd
sudo cp deployment/audio2x.service /etc/systemd/system/
sudo systemctl enable audio2x
sudo systemctl start audio2x
```

## 🔍 Проверка работы

### Health Check
```bash
curl http://your-server:8000/health
```

### Тест Emotions Inference
```bash
curl -X POST http://your-server:8000/infer/emotions \
  -F "audio=@sample-data/audio_1sec_16k_s16le.wav"
```

### Тест Blendshapes Inference
```bash
curl -X POST http://your-server:8000/infer/blendshapes \
  -F "audio=@sample-data/audio_4sec_16k_s16le.wav"
```

## 📊 Мониторинг

### Docker Compose
```bash
docker compose logs -f              # Все логи
docker compose logs -f audio2x      # Логи сервиса
docker compose ps                   # Статус контейнеров
docker stats                        # Использование ресурсов
```

### Systemd
```bash
journalctl -u audio2x -f            # Логи в реальном времени
journalctl -u audio2x --since today # Сегодняшние логи
systemctl status audio2x            # Статус
```

### GPU мониторинг
```bash
nvidia-smi                          # Текущее состояние
watch -n 1 nvidia-smi               # Обновление каждую секунду
```

## 🔒 Безопасность

### Настройка файрвола
```bash
# UFW
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable

# Или только для определенных IP
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

### SSL сертификат (Let's Encrypt)
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Ограничение доступа к API
Раскомментируйте секцию NGINX в `docker-compose.yml` и используйте `nginx.conf` для:
- Rate limiting
- IP whitelisting
- SSL/TLS
- Request size limits

## 🛠 Troubleshooting

### Проблема: GPU не обнаружен
```bash
# Проверка Docker GPU
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Переустановка nvidia-container-toolkit
sudo apt-get purge nvidia-container-toolkit
sudo apt-get install nvidia-container-toolkit
sudo systemctl restart docker
```

### Проблема: Ошибка загрузки моделей
```bash
# Проверьте HF_TOKEN
docker compose exec audio2x env | grep HF_TOKEN

# Переустановка моделей
docker compose exec audio2x bash
hf auth login --token YOUR_TOKEN
./download_models.sh
./gen_testdata.sh
```

### Проблема: Out of memory
```bash
# Проверьте использование памяти
nvidia-smi

# Ограничьте ресурсы в docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G
```

## 📚 Полезные ссылки

- [Основная документация по деплою](../DEPLOYMENT.md)
- [Docker Compose файл](../docker-compose.yml)
- [Dockerfile](../Dockerfile)
- [Основной README](../README.md)

## 💡 Советы

1. **Используйте NGINX** как reverse proxy в продакшене
2. **Настройте мониторинг** (Prometheus + Grafana)
3. **Регулярно обновляйте** Docker образы
4. **Делайте бэкапы** конфигурации и моделей
5. **Логируйте все** для debugging

## 📝 Контрольный список деплоя

- [ ] Сервер с NVIDIA GPU
- [ ] Docker и NVIDIA Container Toolkit установлены
- [ ] Hugging Face токен получен
- [ ] Лицензия на модель принята
- [ ] Файрвол настроен
- [ ] SSL сертификат установлен (для продакшена)
- [ ] Мониторинг настроен
- [ ] Бэкапы настроены
- [ ] Документация обновлена

---

**Нужна помощь?** Создайте issue на [GitHub](https://github.com/NVIDIA/Audio2Face-3D-SDK/issues)

