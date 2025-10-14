# Анализ и исправление ошибки сборки Docker

## Проблема

При сборке Docker-образа возникала ошибка на этапе выполнения скриптов `fetch_deps.sh` и `build.sh`:

```
failed to solve: process "/bin/sh -c if [ \"${SKIP_BUILD}\" = \"1\" ]; then       
  echo \"Skipping SDK build at image build time\";     
else       
  ./fetch_deps.sh release && ./build.sh all release;     
fi" did not complete successfully: exit code: 1
```

## Причины ошибки

1. **Отсутствие прав на выполнение скриптов**
   - При копировании файлов в Docker-контейнер через `COPY . /app` права на выполнение не всегда сохраняются
   - Скрипты `fetch_deps.sh`, `build.sh` и `tools/packman/packman` не имели прав на выполнение

2. **Дублирование логики в build.sh**
   - В скрипте `build.sh` была дублированная логика парсинга аргументов (строки 5-21 и 29-43)
   - Это приводило к перезаписи переменных `BUILD_CONFIG` и `BUILD_PROJECT`
   - Команда `clean` обрабатывалась после парсинга аргументов, что могло вызвать проблемы

3. **Недостаточная диагностика**
   - Скрипты не выводили подробную информацию о процессе выполнения
   - Было сложно определить, на каком именно этапе происходила ошибка

## Внесенные исправления

### 1. Dockerfile

Добавлена установка прав на выполнение для всех необходимых скриптов:

```dockerfile
# Set executable permissions for scripts
RUN chmod +x fetch_deps.sh build.sh download_models.sh gen_testdata.sh run_sample.sh && \
    chmod +x tools/packman/packman
```

Добавлен более подробный вывод в процессе сборки:

```dockerfile
RUN if [ "${SKIP_BUILD}" = "1" ]; then \
      echo "Skipping SDK build at image build time"; \
    else \
      echo "Starting dependency fetch..." && \
      ./fetch_deps.sh release && \
      echo "Dependencies fetched successfully. Starting build..." && \
      ./build.sh all release && \
      echo "Build completed successfully."; \
    fi
```

### 2. fetch_deps.sh

- Добавлен `set -e` для немедленного выхода при ошибке
- Добавлена проверка существования и прав на выполнение packman
- Добавлен подробный вывод на каждом этапе
- Улучшена обработка ошибок с понятными сообщениями

### 3. build.sh

- Исправлена дублированная логика парсинга аргументов
- Команда `clean` теперь обрабатывается в первую очередь
- Добавлен подробный вывод конфигурации сборки
- Улучшены сообщения об ошибках
- Добавлен вывод PATH при ошибке поиска ninja

## Как использовать

### Обычная сборка

```bash
docker-compose build
```

или

```bash
docker build -t audio2x-sdk:latest .
```

### Сборка без компиляции SDK (для Apple Silicon)

```bash
docker build --build-arg SKIP_BUILD=1 -t audio2x-sdk:latest .
```

В этом случае сборка SDK будет выполнена при запуске контейнера, если установлена переменная окружения `BUILD_IN_CONTAINER=1`.

### Отладка

Если сборка все еще падает, можно запустить контейнер в интерактивном режиме:

```bash
docker run -it --rm audio2x-sdk:latest /bin/bash
```

И выполнить команды вручную:

```bash
cd /app
./fetch_deps.sh release
./build.sh all release
```

## Дополнительные рекомендации

1. **Проверка прав на файлы**
   - Убедитесь, что все `.sh` файлы имеют права на выполнение в вашем репозитории
   - Используйте `git ls-files --stage` для проверки прав в Git

2. **Git LFS**
   - Убедитесь, что Git LFS установлен и инициализирован
   - Проверьте, что все большие файлы корректно загружены

3. **Сетевой доступ**
   - Packman требует доступа к интернету для загрузки зависимостей
   - Убедитесь, что Docker имеет доступ к сети во время сборки

4. **Логирование**
   - Все скрипты теперь выводят подробную информацию
   - При возникновении ошибки проверьте логи Docker для определения точного места сбоя

## Изменения в файлах

- ✅ `Dockerfile` - добавлены права на выполнение и улучшен вывод
- ✅ `fetch_deps.sh` - добавлена диагностика и обработка ошибок
- ✅ `build.sh` - исправлена логика парсинга аргументов и добавлен вывод
- ✅ `audio2face-sdk/source/tools/a2f_geometry_npz.cpp` - исправлен callback (добавлен return type)

## Тестирование

После внесения изменений рекомендуется:

1. Очистить кэш Docker:
   ```bash
   docker system prune -a
   ```

2. Пересобрать образ:
   ```bash
   docker-compose build --no-cache
   ```

3. Запустить контейнер:
   ```bash
   docker-compose up
   ```

4. Проверить работоспособность:
   ```bash
   curl http://localhost:8000/health
   ```

