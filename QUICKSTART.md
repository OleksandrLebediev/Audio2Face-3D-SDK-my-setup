# 🚀 Быстрый старт Audio2Face-3D SDK

## Вариант 1: Деплой на сервер (рекомендуется)

### Один шаг:

```bash
./deployment/deploy.sh user@server-ip hf_ваш_токен
```

Скрипт автоматически:
- ✅ Установит Docker и NVIDIA Container Toolkit
- ✅ Склонирует репозиторий
- ✅ Загрузит модели (~5-10 GB)
- ✅ Соберет и запустит сервис
- ✅ Проверит работоспособность

### Пример:

```bash
# Получите токен: https://huggingface.co/settings/tokens
# Примите лицензии на модели (см. ниже)

./deployment/deploy.sh ubuntu@192.168.1.100 hf_abc123xyz456
```

### Требования:

1. **SSH доступ** к серверу
2. **NVIDIA GPU** с установленными драйверами
3. **HuggingFace токен** с принятыми лицензиями:
   - https://huggingface.co/nvidia/Audio2Face-3D-v3.0
   - https://huggingface.co/nvidia/Audio2Emotion-v2.2

---

## Вариант 2: Локальная разработка с Docker Compose

### Шаг 1: Загрузите модели

```bash
# Установите токен
export HF_TOKEN=hf_ваш_токен

# Загрузите модели
./download_models.sh
```

### Шаг 2: Запустите сервис

```bash
docker-compose up -d
```

### Шаг 3: Проверьте

```bash
curl http://localhost:8000/health
```

---

## Вариант 3: Локальная разработка без Docker

### Требования:

- CUDA 12.4+
- TensorRT 10.0+
- Python 3.10+
- CMake 3.24+
- Ninja

### Сборка:

```bash
# 1. Установите зависимости Python
pip install -r deps/requirements.txt
pip install -r requirements-service.txt

# 2. Загрузите модели
export HF_TOKEN=hf_ваш_токен
./download_models.sh

# 3. Соберите SDK
./fetch_deps.sh release
./build.sh all release

# 4. Запустите сервер
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

---

## 🔧 Настройка переменных окружения (опционально)

Если вы используете `docker-compose` и хотите изменить настройки по умолчанию, создайте файл `.env`:

```bash
# .env (опционально)
HF_TOKEN=hf_ваш_токен
DOWNLOAD_MODELS=1    # Загрузить модели при старте контейнера
SERVER_PORT=8000
BUILD_TYPE=release
```

**Но это НЕ обязательно!** Docker Compose использует разумные значения по умолчанию.

---

## 📝 Полезные команды

### Деплой:

```bash
# Деплой с токеном
./deployment/deploy.sh user@server hf_token

# Деплой без токена (загрузите модели вручную потом)
./deployment/deploy.sh user@server

# Проверить логи на сервере
ssh user@server "cd Audio2Face-3D-SDK && docker compose logs -f"

# Перезапустить на сервере
ssh user@server "cd Audio2Face-3D-SDK && docker compose restart"
```

### Локальная разработка:

```bash
# Запуск
docker-compose up -d

# Логи
docker-compose logs -f

# Остановка
docker-compose down

# Пересборка
docker-compose up -d --build

# Войти в контейнер
docker-compose exec audio2x bash
```

---

## 🎯 Что выбрать?

| Сценарий | Рекомендация |
|----------|--------------|
| **Продакшен деплой** | Вариант 1 (deploy.sh) |
| **Локальная разработка** | Вариант 2 (Docker Compose) |
| **Разработка SDK** | Вариант 3 (Нативная сборка) |

---

## 🚨 Решение проблем

### Модели не загружаются

```bash
# На сервере после деплоя
ssh user@server
cd Audio2Face-3D-SDK
export HF_TOKEN=hf_ваш_токен
./download_models.sh
docker compose restart
```

### Ошибка сборки Docker

```bash
# Очистите кэш
docker system prune -a

# Пересоберите
docker-compose build --no-cache
```

### Порт занят

```bash
# Измените порт
export SERVER_PORT=8001
docker-compose up -d
```

---

## 📚 Дополнительная документация

- [MODEL_DOWNLOAD_GUIDE.md](MODEL_DOWNLOAD_GUIDE.md) - Подробно о моделях
- [DOCKER_BUILD_FIX.md](DOCKER_BUILD_FIX.md) - Решение проблем сборки
- [deployment/README.md](deployment/README.md) - Детали деплоя
- [deployment/deploy.sh](deployment/deploy.sh) - Скрипт автоматического деплоя

