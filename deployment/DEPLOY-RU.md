# 🇷🇺 Инструкция по развертыванию на сервере через SSH

## Быстрый старт

### Шаг 1: Подготовка

1. **Получите Hugging Face токен**:
   - Зарегистрируйтесь на https://huggingface.co
   - Создайте токен: https://huggingface.co/settings/tokens
   - Примите лицензию: https://huggingface.co/nvidia/Audio2Emotion-v2.2

2. **Требования к серверу**:
   - Ubuntu 20.04+ с NVIDIA GPU
   - CUDA 12.8+
   - Docker установлен
   - SSH доступ

### Шаг 2: Автоматический деплой (самый простой способ)

```bash
cd Audio2Face-3D-SDK/deployment
chmod +x deploy.sh
./deploy.sh ubuntu@192.168.1.100 ВАШ_HF_ТОКЕН
```

Скрипт автоматически:
- ✅ Установит Docker и NVIDIA Container Toolkit
- ✅ Склонирует проект на сервер
- ✅ Настроит окружение
- ✅ Соберет и запустит сервис
- ✅ Проверит работоспособность

**Готово!** Сервис доступен на `http://ВАШ_СЕРВЕР:8000`

---

## Альтернативный способ: Ручная установка

### 1. Подключитесь к серверу:

```bash
ssh ubuntu@ваш-сервер
```

### 2. Установите Docker (если не установлен):

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 3. Установите NVIDIA Container Toolkit:

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 4. Проверьте GPU:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

### 5. Склонируйте проект:

```bash
git clone https://github.com/NVIDIA/Audio2Face-3D-SDK.git
cd Audio2Face-3D-SDK
git lfs pull
```

### 6. Создайте файл .env:

```bash
cat > .env << EOF
BUILD_TYPE=release
HF_TOKEN=ваш_huggingface_токен
DOWNLOAD_MODELS=1
SERVER_PORT=8000
CUDA_PATH=/usr/local/cuda
TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu
EOF
```

### 7. Запустите сервис:

```bash
docker compose up -d
```

### 8. Просмотрите логи:

```bash
docker compose logs -f
```

---

## Проверка работы

### Проверка здоровья сервиса:

```bash
curl http://localhost:8000/health
```

### Тест определения эмоций:

```bash
curl -X POST http://localhost:8000/infer/emotions \
  -F "audio=@sample-data/audio_1sec_16k_s16le.wav"
```

### Тест генерации анимации:

```bash
curl -X POST http://localhost:8000/infer/blendshapes \
  -F "audio=@sample-data/audio_4sec_16k_s16le.wav"
```

---

## Управление сервисом

### Просмотр логов:
```bash
docker compose logs -f
```

### Перезапуск:
```bash
docker compose restart
```

### Остановка:
```bash
docker compose down
```

### Обновление:
```bash
git pull
docker compose up -d --build
```

### Проверка статуса:
```bash
docker compose ps
nvidia-smi  # мониторинг GPU
```

---

## Открытие доступа извне

### Настройка файрвола:

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

### Настройка облачного провайдера:

- **AWS**: Security Groups → добавьте порт 8000
- **Google Cloud**: VPC firewall → создайте правило для порта 8000  
- **Azure**: Network Security Group → разрешите порт 8000

---

## Продакшен конфигурация

### 1. Настройка NGINX (reverse proxy):

Раскомментируйте секцию nginx в `docker-compose.yml` или установите на хосте:

```bash
sudo apt-get install nginx
sudo cp deployment/nginx.conf /etc/nginx/sites-available/audio2x
sudo ln -s /etc/nginx/sites-available/audio2x /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. SSL сертификат (Let's Encrypt):

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d ваш-домен.com
```

### 3. Автозапуск при перезагрузке:

Docker Compose автоматически настроен на автозапуск (`restart: unless-stopped`)

Для проверки:
```bash
sudo reboot
# После перезагрузки:
docker compose ps  # должен быть запущен
```

---

## Решение проблем

### GPU не обнаружен:

```bash
# Переустановите nvidia-container-toolkit
sudo apt-get purge nvidia-container-toolkit
sudo apt-get install nvidia-container-toolkit
sudo systemctl restart docker

# Тест
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

### Ошибка загрузки моделей:

```bash
# Убедитесь, что приняли лицензию на HuggingFace:
# https://huggingface.co/nvidia/Audio2Emotion-v2.2

# Проверьте токен
docker compose exec audio2x env | grep HF_TOKEN

# Перезапустите
nano .env  # исправьте HF_TOKEN
docker compose restart
```

### Недостаточно памяти GPU:

```bash
# Проверьте использование
nvidia-smi

# Используйте GPU с минимум 4GB памяти (рекомендуется 8GB+)
```

### Порт уже используется:

```bash
# Измените порт в .env
nano .env
# Замените SERVER_PORT=8000 на SERVER_PORT=8001

docker compose down
docker compose up -d
```

---

## Мониторинг и логи

### Docker логи:
```bash
docker compose logs -f                  # Все логи
docker compose logs -f --tail=100       # Последние 100 строк
docker compose logs audio2x             # Только сервис audio2x
```

### Системные логи (если используете systemd):
```bash
journalctl -u audio2x -f               # Реального времени
journalctl -u audio2x --since today    # Сегодняшние
journalctl -u audio2x --since "1 hour ago"
```

### GPU мониторинг:
```bash
nvidia-smi                             # Текущее состояние
watch -n 1 nvidia-smi                  # Обновление каждую секунду
nvidia-smi dmon                        # Device monitoring
```

### Производительность:
```bash
docker stats                           # Использование CPU/RAM
htop                                   # Системный мониторинг
```

---

## Бэкап и восстановление

### Бэкап моделей:

```bash
# Создайте архив моделей
tar -czf models-backup.tar.gz _data

# Скопируйте на локальный компьютер
scp ubuntu@сервер:~/Audio2Face-3D-SDK/models-backup.tar.gz .
```

### Восстановление:

```bash
# На сервере
tar -xzf models-backup.tar.gz
docker compose restart
```

---

## API Документация

### Health Check
**GET** `/health`

```bash
curl http://localhost:8000/health
```

Ответ:
```json
{
  "status": "ok",
  "build_type": "release",
  "cuda_path": "/usr/local/cuda",
  "tensorrt_root": "/usr/lib/x86_64-linux-gnu"
}
```

### Определение эмоций
**POST** `/infer/emotions`

```bash
curl -X POST http://localhost:8000/infer/emotions \
  -F "audio=@path/to/audio.wav"
```

### Генерация blendshapes
**POST** `/infer/blendshapes`

```bash
curl -X POST http://localhost:8000/infer/blendshapes \
  -F "audio=@path/to/audio.wav"
```

---

## Полезные команды SSH

### Копирование файлов на сервер:
```bash
scp audio.wav ubuntu@сервер:~/
```

### Копирование с сервера:
```bash
scp ubuntu@сервер:~/result.json ./
```

### SSH туннель (доступ к localhost):
```bash
ssh -L 8000:localhost:8000 ubuntu@сервер
# Теперь доступен на http://localhost:8000
```

### Выполнение команды без входа:
```bash
ssh ubuntu@сервер "docker compose logs --tail=50"
```

---

## Чек-лист деплоя

- [ ] Сервер с NVIDIA GPU настроен
- [ ] Docker установлен и работает
- [ ] NVIDIA Container Toolkit установлен
- [ ] Hugging Face токен получен
- [ ] Лицензия на модель принята на HuggingFace
- [ ] Проект склонирован на сервер
- [ ] Файл .env создан с правильным токеном
- [ ] Сервис запущен через docker compose
- [ ] Health check проходит успешно
- [ ] Тесты inference работают
- [ ] Файрвол настроен (если нужен внешний доступ)
- [ ] NGINX настроен (для продакшена)
- [ ] SSL сертификат установлен (для продакшена)
- [ ] Мониторинг настроен
- [ ] Бэкапы настроены

---

## Дополнительные материалы

- [Полная документация по деплою (EN)](../DEPLOYMENT.md)
- [Deployment файлы](README.md)
- [Быстрый деплой (EN)](quick-deploy.md)
- [Основной README](../README.md)

---

## Поддержка

**Вопросы и проблемы**: https://github.com/NVIDIA/Audio2Face-3D-SDK/issues

**Время развертывания**: 
- Автоматический скрипт: **5-10 минут**
- Ручная установка: **15-20 минут**

---

**Удачи с развертыванием! 🚀**

