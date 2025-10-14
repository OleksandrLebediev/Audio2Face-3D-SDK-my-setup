# Руководство по загрузке моделей Audio2Face-3D

## 📦 Какие модели загружаются?

Проект использует несколько моделей из Hugging Face:

### Audio2Face модели (4 модели):
1. **nvidia/Audio2Face-3D-v3.0** - последняя версия
2. **nvidia/Audio2Face-3D-v2.3.1-Claire** - персонаж Claire
3. **nvidia/Audio2Face-3D-v2.3.1-James** - персонаж James
4. **nvidia/Audio2Face-3D-v2.3-Mark** - персонаж Mark

### Audio2Emotion модели (1 модель):
5. **nvidia/Audio2Emotion-v2.2** - модель эмоций

Все модели сохраняются в директорию `_data/`:
- Audio2Face: `_data/audio2face-models/`
- Audio2Emotion: `_data/audio2emotion-models/`

## 🔄 Когда происходит загрузка моделей?

Есть **3 основных сценария** загрузки моделей:

### 1️⃣ При запуске Docker-контейнера (автоматически)

**Условия:**
- Переменная окружения `DOWNLOAD_MODELS=1` в `.env` или `docker-compose.yml`
- Переменная `HF_TOKEN` установлена с валидным токеном Hugging Face

**Как это работает:**
```bash
# В docker/entrypoint.sh (строки 30-37)
if [[ "${DOWNLOAD_MODELS:-0}" == "1" ]]; then
  if [[ -n "${HF_TOKEN:-}" ]]; then
    hf auth login --token "${HF_TOKEN}"
  fi
  ./download_models.sh
  ./gen_testdata.sh
fi
```

**Когда запускается:**
- При первом запуске контейнера: `docker-compose up`
- При перезапуске контейнера: `docker-compose restart`
- При ручном запуске: `docker run ...`

### 2️⃣ При деплое через deploy.sh (автоматически)

**Условия:**
- Вы передали HF_TOKEN как второй аргумент скрипту
- Директория `_data/audio2face-models` пуста или не существует

**Команда:**
```bash
./deployment/deploy.sh user@server-ip hf_ваш_токен
```

**Как это работает:**
```bash
# В deploy.sh (строки 110-136)
if [ -n "$HF_TOKEN" ]; then
    ssh "$SERVER" << EOF
cd Audio2Face-3D-SDK
if [ ! -d "_data/audio2face-models" ] || [ -z "\$(ls -A _data/audio2face-models 2>/dev/null)" ]; then
    export HF_TOKEN=${HF_TOKEN}
    chmod +x download_models.sh
    ./download_models.sh
fi
EOF
fi
```

### 3️⃣ Вручную (локально или на сервере)

**Команда:**
```bash
# Установите токен
export HF_TOKEN=ваш_токен_huggingface

# Запустите скрипт
./download_models.sh
```

## 🔑 Как получить HF_TOKEN?

1. Зарегистрируйтесь на [Hugging Face](https://huggingface.co/)
2. Перейдите в [Settings → Access Tokens](https://huggingface.co/settings/tokens)
3. Создайте новый токен с правами `read`
4. **ВАЖНО:** Примите лицензию для моделей:
   - https://huggingface.co/nvidia/Audio2Face-3D-v3.0
   - https://huggingface.co/nvidia/Audio2Emotion-v2.2

## ⚙️ Настройка переменных окружения

### Для Docker Compose

Создайте файл `.env` в корне проекта:

```bash
# .env
BUILD_TYPE=release
SKIP_BUILD=0
CUDA_PATH=/usr/local/cuda
TENSORRT_ROOT_DIR=/usr/lib/x86_64-linux-gnu
HF_TOKEN=hf_ваш_токен_здесь
DOWNLOAD_MODELS=1          # ← Включить автозагрузку
RUN_UNIT_TESTS=0
BUILD_IN_CONTAINER=0
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
```

### Для ручного запуска Docker

```bash
docker run -it --rm --gpus all \
  -e HF_TOKEN=hf_ваш_токен \
  -e DOWNLOAD_MODELS=1 \
  -v $(pwd)/_data:/app/_data \
  audio2x-sdk:latest
```

## 📋 Детали работы download_models.sh

Скрипт `download_models.sh` делает следующее:

```bash
#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$BASE_DIR/_data"

# Создает директории
A2F_MODEL_DIR="$BASE_DIR/_data/audio2face-models"
A2E_MODEL_DIR="$BASE_DIR/_data/audio2emotion-models"

# Загружает 4 модели Audio2Face
python -m huggingface_hub.commands.huggingface_cli download \
  nvidia/Audio2Face-3D-v3.0 \
  --local-dir "$A2F_MODEL_DIR/audio2face-3d-v3.0"

python -m huggingface_hub.commands.huggingface_cli download \
  nvidia/Audio2Face-3D-v2.3.1-Claire \
  --local-dir "$A2F_MODEL_DIR/audio2face-3d-v2.3.1-claire"

python -m huggingface_hub.commands.huggingface_cli download \
  nvidia/Audio2Face-3D-v2.3.1-James \
  --local-dir "$A2F_MODEL_DIR/audio2face-3d-v2.3.1-james"

python -m huggingface_hub.commands.huggingface_cli download \
  nvidia/Audio2Face-3D-v2.3-Mark \
  --local-dir "$A2F_MODEL_DIR/audio2face-3d-v2.3-mark"

# Загружает модель Audio2Emotion
python -m huggingface_hub.commands.huggingface_cli download \
  nvidia/Audio2Emotion-v2.2 \
  --local-dir $A2E_MODEL_DIR/audio2emotion-v2.2
```

## 🔍 Проверка загруженных моделей

### Проверить наличие моделей:

```bash
# Локально
ls -la _data/audio2face-models/
ls -la _data/audio2emotion-models/

# В Docker-контейнере
docker-compose exec audio2x ls -la /app/_data/audio2face-models/
docker-compose exec audio2x ls -la /app/_data/audio2emotion-models/
```

### Ожидаемая структура:

```
_data/
├── audio2face-models/
│   ├── audio2face-3d-v3.0/
│   │   ├── model.onnx
│   │   ├── config.json
│   │   └── ...
│   ├── audio2face-3d-v2.3.1-claire/
│   ├── audio2face-3d-v2.3.1-james/
│   └── audio2face-3d-v2.3-mark/
└── audio2emotion-models/
    └── audio2emotion-v2.2/
        ├── model.onnx
        └── ...
```

## 🚨 Решение проблем

### Проблема: Модели не загружаются

**Причина 1:** Не установлен HF_TOKEN
```bash
# Проверить
docker-compose exec audio2x env | grep HF_TOKEN

# Решение: добавить в .env
echo "HF_TOKEN=hf_ваш_токен" >> .env
docker-compose restart
```

**Причина 2:** Не принята лицензия на Hugging Face
```bash
# Решение: перейти по ссылкам и принять лицензию
# https://huggingface.co/nvidia/Audio2Face-3D-v3.0
# https://huggingface.co/nvidia/Audio2Emotion-v2.2
```

**Причина 3:** DOWNLOAD_MODELS=0
```bash
# Проверить
cat .env | grep DOWNLOAD_MODELS

# Решение: изменить на 1
sed -i 's/DOWNLOAD_MODELS=0/DOWNLOAD_MODELS=1/' .env
docker-compose restart
```

### Проблема: Загрузка прерывается

**Причина:** Нестабильное интернет-соединение

**Решение:** Загрузить модели вручную с повторными попытками
```bash
# Войти в контейнер
docker-compose exec audio2x bash

# Запустить с повторами
for i in {1..3}; do
  ./download_models.sh && break || sleep 10
done
```

### Проблема: Недостаточно места на диске

**Размер моделей:** ~5-10 GB

**Проверить место:**
```bash
df -h _data/
```

**Решение:** Освободить место или использовать другой volume

## 💡 Оптимизация

### Загрузить только нужные модели

Отредактируйте `download_models.sh` и закомментируйте ненужные модели:

```bash
# Оставить только v3.0
python -m huggingface_hub.commands.huggingface_cli download \
  nvidia/Audio2Face-3D-v3.0 \
  --local-dir "$A2F_MODEL_DIR/audio2face-3d-v3.0"

# Закомментировать остальные
# python -m huggingface_hub.commands.huggingface_cli download \
#   nvidia/Audio2Face-3D-v2.3.1-Claire ...
```

### Использовать общий volume для моделей

В `docker-compose.yml`:

```yaml
volumes:
  - /path/to/shared/models:/app/_data:ro  # read-only
```

Это позволит использовать одни модели для нескольких контейнеров.

## 📝 Резюме

| Сценарий | Когда | Условия | Команда |
|----------|-------|---------|---------|
| **Docker Compose** | При запуске контейнера | `DOWNLOAD_MODELS=1` + `HF_TOKEN` | `docker-compose up` |
| **Deploy Script** | При деплое на сервер | Передан HF_TOKEN | `./deploy.sh user@server token` |
| **Вручную** | Когда нужно | `HF_TOKEN` установлен | `./download_models.sh` |

**Рекомендация:** Для продакшена лучше загрузить модели один раз вручную и использовать volume, чтобы не загружать их при каждом перезапуске контейнера.

