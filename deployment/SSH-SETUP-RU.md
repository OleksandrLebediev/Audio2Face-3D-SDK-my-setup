# 🔑 Настройка SSH для доступа к серверу

## Генерация SSH ключей

### Для macOS/Linux:

```bash
# 1. Генерация SSH ключа (Ed25519 - современный и безопасный алгоритм)
ssh-keygen -t ed25519 -C "ваш_email@example.com"

# Или используйте RSA (если сервер не поддерживает Ed25519)
ssh-keygen -t rsa -b 4096 -C "ваш_email@example.com"
```

**Процесс генерации:**
```
Generating public/private ed25519 key pair.
Enter file in which to save the key (/Users/username/.ssh/id_ed25519): [Enter]
Enter passphrase (empty for no passphrase): [введите пароль или Enter для пропуска]
Enter same passphrase again: [повторите пароль]
```

**Ваш ключ создан!**
- Приватный ключ: `~/.ssh/id_ed25519` (НИКОМУ НЕ ПОКАЗЫВАЙТЕ!)
- Публичный ключ: `~/.ssh/id_ed25519.pub` (можно копировать на сервер)

---

## Копирование ключа на сервер

### Способ 1: Автоматический (рекомендуется)

```bash
# Скопировать публичный ключ на сервер
ssh-copy-id -i ~/.ssh/id_ed25519.pub ubuntu@ваш-сервер

# Если используется нестандартный порт
ssh-copy-id -i ~/.ssh/id_ed25519.pub -p 2222 ubuntu@ваш-сервер
```

### Способ 2: Ручной

```bash
# 1. Скопируйте содержимое публичного ключа
cat ~/.ssh/id_ed25519.pub
# Скопируйте вывод (начинается с ssh-ed25519...)

# 2. Подключитесь к серверу
ssh ubuntu@ваш-сервер

# 3. На сервере добавьте ключ
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "СЮДА_ВСТАВЬТЕ_ПУБЛИЧНЫЙ_КЛЮЧ" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
exit
```

### Способ 3: Через облачный провайдер

#### AWS EC2:
1. При создании инстанса выберите "Create new key pair"
2. Скачайте приватный ключ (например, `mykey.pem`)
3. Используйте:
```bash
chmod 400 mykey.pem
ssh -i mykey.pem ubuntu@ec2-ip-address
```

#### Google Cloud:
1. Compute Engine → Metadata → SSH Keys
2. Нажмите "Add SSH key"
3. Вставьте содержимое `~/.ssh/id_ed25519.pub`

#### Azure:
1. При создании VM выберите "SSH public key"
2. Вставьте содержимое `~/.ssh/id_ed25519.pub`

---

## Проверка подключения

```bash
# Тестовое подключение
ssh ubuntu@ваш-сервер

# Если нужен специфический ключ
ssh -i ~/.ssh/id_ed25519 ubuntu@ваш-сервер

# С нестандартным портом
ssh -p 2222 ubuntu@ваш-сервер
```

---

## Настройка SSH конфигурации (упрощает подключение)

Создайте/отредактируйте файл `~/.ssh/config`:

```bash
nano ~/.ssh/config
```

Добавьте:

```ssh
# Ваш сервер для Audio2X
Host audio2x
    HostName 192.168.1.100
    User ubuntu
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Или для нескольких серверов
Host audio2x-prod
    HostName prod.example.com
    User ubuntu
    IdentityFile ~/.ssh/id_ed25519

Host audio2x-dev
    HostName dev.example.com
    User ubuntu
    IdentityFile ~/.ssh/id_ed25519_dev
```

Теперь можно подключаться просто:

```bash
ssh audio2x
# Вместо: ssh -i ~/.ssh/id_ed25519 ubuntu@192.168.1.100
```

---

## Использование с deploy.sh

После настройки SSH, используйте скрипт деплоя:

```bash
# Если настроен ~/.ssh/config
cd deployment
./deploy.sh audio2x ваш_hf_токен

# Или напрямую
./deploy.sh ubuntu@192.168.1.100 ваш_hf_токен

# С нестандартным портом
ssh -p 2222 ubuntu@сервер  # сначала проверьте подключение
# затем используйте deploy.sh с этим адресом
```

---

## Безопасность SSH

### 1. Настройка сервера (на сервере выполните):

```bash
sudo nano /etc/ssh/sshd_config
```

Рекомендуемые настройки:

```conf
# Отключить пароли (использовать только ключи)
PasswordAuthentication no
ChallengeResponseAuthentication no

# Отключить вход для root
PermitRootLogin no

# Разрешить вход только определенным пользователям
AllowUsers ubuntu

# Изменить порт SSH (опционально, для безопасности)
Port 2222

# Использовать только безопасные алгоритмы
KexAlgorithms curve25519-sha256@libssh.org
HostKeyAlgorithms ssh-ed25519
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com

# Ограничить попытки входа
MaxAuthTries 3
MaxSessions 5

# Таймаут
ClientAliveInterval 300
ClientAliveCountMax 2
```

Перезапустите SSH:
```bash
sudo systemctl restart sshd
```

### 2. Настройка файрвола:

```bash
# Разрешить только SSH с определенных IP
sudo ufw allow from 192.168.1.0/24 to any port 22
sudo ufw allow 8000/tcp
sudo ufw enable

# Или для всех (менее безопасно)
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw enable
```

### 3. Установка fail2ban (защита от брутфорса):

```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## SSH Agent (для удобства)

### Добавить ключ в SSH Agent:

```bash
# Запустить агент
eval "$(ssh-agent -s)"

# Добавить ключ
ssh-add ~/.ssh/id_ed25519

# Проверить добавленные ключи
ssh-add -l

# Добавить в конфиг для macOS (постоянное хранение)
echo "Host *
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519" >> ~/.ssh/config
```

Теперь не нужно каждый раз вводить пароль от ключа!

---

## SSH Tunneling (доступ к localhost сервера)

### Локальный туннель:

```bash
# Перенаправить порт 8000 с сервера на ваш localhost:8000
ssh -L 8000:localhost:8000 ubuntu@сервер

# Теперь доступен на http://localhost:8000
```

### Обратный туннель (expose вашего localhost на сервер):

```bash
# Ваш localhost:3000 доступен на сервере как localhost:3000
ssh -R 3000:localhost:3000 ubuntu@сервер
```

### SOCKS прокси:

```bash
# Создать SOCKS прокси через SSH
ssh -D 9999 ubuntu@сервер

# Настройте браузер использовать localhost:9999 как SOCKS5 прокси
```

---

## Копирование файлов через SSH

### SCP (Secure Copy):

```bash
# С локального на сервер
scp audio.wav ubuntu@сервер:/home/ubuntu/
scp -r ./models ubuntu@сервер:/home/ubuntu/

# С сервера на локальный
scp ubuntu@сервер:/home/ubuntu/result.json ./
scp -r ubuntu@сервер:/home/ubuntu/logs ./

# С использованием config
scp audio.wav audio2x:/home/ubuntu/
```

### RSYNC (лучше для больших файлов):

```bash
# Синхронизация папки
rsync -avz ./models ubuntu@сервер:/home/ubuntu/
rsync -avz --progress ./models ubuntu@сервер:/home/ubuntu/

# С использованием config
rsync -avz ./models audio2x:/home/ubuntu/

# С исключениями
rsync -avz --exclude '*.pyc' --exclude '__pycache__' ./models ubuntu@сервер:/home/ubuntu/
```

---

## Решение проблем

### Проблема: Permission denied (publickey)

```bash
# Проверьте права доступа на ключи
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub

# На сервере проверьте
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### Проблема: Too many authentication failures

```bash
# Укажите конкретный ключ
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 ubuntu@сервер
```

### Проблема: Host key verification failed

```bash
# Удалите старый ключ хоста
ssh-keygen -R сервер-ip-или-hostname

# Или отключите проверку (небезопасно!)
ssh -o StrictHostKeyChecking=no ubuntu@сервер
```

### Проблема: Connection timeout

```bash
# Проверьте, открыт ли порт
nc -zv сервер-ip 22

# Проверьте файрвол
sudo ufw status

# Используйте verbose режим для диагностики
ssh -vvv ubuntu@сервер
```

---

## Мультиплексирование SSH (несколько сессий через одно соединение)

В `~/.ssh/config`:

```ssh
Host *
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h-%p
    ControlPersist 600
```

Создайте папку:
```bash
mkdir -p ~/.ssh/sockets
```

Теперь повторные подключения будут мгновенными!

---

## Полезные команды

```bash
# Выполнить команду без входа
ssh ubuntu@сервер "docker ps"
ssh ubuntu@сервер "cat /var/log/syslog | tail -20"

# Множественные команды
ssh ubuntu@сервер "cd Audio2Face-3D-SDK && docker compose logs --tail=50"

# С перенаправлением вывода
ssh ubuntu@сервер "docker compose logs" > local-logs.txt

# Интерактивная команда
ssh -t ubuntu@сервер "sudo nano /etc/nginx/nginx.conf"

# Выполнить локальный скрипт на сервере
ssh ubuntu@сервер 'bash -s' < local-script.sh

# С переменными
ssh ubuntu@сервер "export VAR=value && ./script.sh"
```

---

## ⚠️ ВАЖНО: Безопасность токенов

Вы добавили HF_TOKEN в `deployment/env.example`. **Это небезопасно!**

### ❌ НЕ ДЕЛАЙТЕ:
```bash
# НЕ коммитьте настоящие токены!
git add deployment/env.example  # с настоящим токеном
```

### ✅ ПРАВИЛЬНО:

1. **Создайте .env локально (он в .gitignore)**:
```bash
cp deployment/env.example .env
nano .env  # добавьте настоящий токен
```

2. **Или передавайте токен через скрипт**:
```bash
./deployment/deploy.sh ubuntu@сервер ВАШ_HF_ТОКЕН
```

3. **Или используйте переменные окружения**:
```bash
export HF_TOKEN=ваш_токен
./deployment/deploy.sh ubuntu@сервер $HF_TOKEN
```

4. **Верните env.example в исходное состояние**:
```bash
cd deployment
git checkout env.example  # откатить изменения
```

---

## Чек-лист SSH настройки

- [ ] SSH ключи сгенерированы (`ssh-keygen -t ed25519`)
- [ ] Публичный ключ скопирован на сервер (`ssh-copy-id`)
- [ ] Подключение работает без пароля
- [ ] `~/.ssh/config` настроен для удобства
- [ ] Права доступа к файлам правильные (700/600)
- [ ] SSH Agent настроен (опционально)
- [ ] Файрвол на сервере настроен
- [ ] fail2ban установлен (рекомендуется)
- [ ] Пароли отключены на сервере
- [ ] Root вход отключен
- [ ] Токены не коммитятся в git

---

## Быстрая справка

```bash
# Генерация ключа
ssh-keygen -t ed25519 -C "email@example.com"

# Копирование на сервер
ssh-copy-id ubuntu@сервер

# Подключение
ssh ubuntu@сервер

# С туннелем
ssh -L 8000:localhost:8000 ubuntu@сервер

# Копирование файлов
scp file.txt ubuntu@сервер:/path/
rsync -avz folder/ ubuntu@сервер:/path/

# Выполнение команды
ssh ubuntu@сервер "команда"

# Деплой проекта
./deployment/deploy.sh ubuntu@сервер токен
```

---

**Готово! Теперь у вас безопасный доступ к серверу через SSH 🔐**

