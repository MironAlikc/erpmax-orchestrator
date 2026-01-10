# Інструкції з розгортання ERPMax Orchestrator

## Перше розгортання

### Передумови

1. **На локальній машині:**
   - Git
   - SSH доступ до віддаленого сервера
   - rsync (зазвичай встановлений на macOS/Linux)

2. **На віддаленому сервері:**
   - Ubuntu/Debian Linux (рекомендовано)
   - Мінімум 2GB RAM
   - Мінімум 20GB вільного місця на диску
   - Відкритий порт 8000 для API

### Крок 1: Налаштування SSH

Додайте SSH ключ для автоматичного входу (опціонально, але рекомендовано):

```bash
# Згенеруйте SSH ключ (якщо ще не маєте)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Скопіюйте ключ на сервер
ssh-copy-id feras1960@192.168.0.83
```

Або використовуйте пароль: `bF8ayJJu`

### Крок 2: Запуск розгортання

```bash
# Зробіть скрипт виконуваним
chmod +x deploy.sh

# Запустіть розгортання
./deploy.sh
```

Скрипт автоматично:

- ✅ Перевірить SSH з'єднання
- ✅ Встановить Docker та Docker Compose (якщо потрібно)
- ✅ Створить директорію проекту
- ✅ Скопіює файли проекту
- ✅ Згенерує безпечні паролі та SECRET_KEY
- ✅ Запустить Docker контейнери
- ✅ Виконає міграції бази даних
- ✅ Перевірить здоров'я API

### Крок 3: Перевірка

Після успішного розгортання перевірте:

```bash
# Перевірка здоров'я API
curl http://192.168.0.83:8000/health

# Відкрийте в браузері
http://192.168.0.83:8000/docs
```

---

## Оновлення додатка

Для оновлення вже розгорнутого додатка:

```bash
# Зробіть скрипт виконуваним (один раз)
chmod +x update.sh

# Запустіть оновлення
./update.sh
```

Скрипт оновлення:

- ✅ Копіює нові файли
- ✅ Зупиняє додаток (БД продовжує працювати)
- ✅ Перебудовує Docker образи
- ✅ Виконує міграції
- ✅ Запускає оновлений додаток
- ✅ Перевіряє здоров'я

---

## Корисні команди

### Перегляд логів

```bash
# Всі сервіси
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml logs -f'

# Тільки додаток
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker logs -f erpmax_orchestrator'

# Тільки база даних
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker logs -f erpmax_postgres'

# Міграції
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker logs erpmax_migration'
```

### Перезапуск сервісів

```bash
# Перезапустити всі сервіси
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml restart'

# Перезапустити тільки додаток
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml restart app'
```

### Зупинка сервісів

```bash
# Зупинити всі сервіси
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml down'

# Зупинити з видаленням volumes (УВАГА: видалить дані!)
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml down -v'
```

### Статус сервісів

```bash
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml ps'
```

### Backup бази даних

```bash
# Створити backup
ssh feras1960@192.168.0.83 'docker exec erpmax_postgres pg_dump -U erpmax erpmax_orchestrator > ~/backup_$(date +%Y%m%d_%H%M%S).sql'

# Завантажити backup на локальну машину
scp feras1960@192.168.0.83:~/backup_*.sql ./backups/
```

### Відновлення з backup

```bash
# Завантажити backup на сервер
scp ./backups/backup_20231218_120000.sql feras1960@192.168.0.83:~/

# Відновити
ssh feras1960@192.168.0.83 'docker exec -i erpmax_postgres psql -U erpmax erpmax_orchestrator < ~/backup_20231218_120000.sql'
```

---

## Налаштування production

### Редагування .env.production

```bash
# Підключитися до сервера
ssh feras1960@192.168.0.83

# Відредагувати файл
cd /home/feras1960/erpmax-orchestrator
nano .env.production
```

Важливі параметри:

```bash
# Домени для CORS
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Stripe (якщо використовується)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# LiqPay (якщо використовується)
LIQPAY_PUBLIC_KEY=...
LIQPAY_PRIVATE_KEY=...

# ERPNext
ERPNEXT_BASE_URL=https://erpnext.yourdomain.com
```

Після змін перезапустіть:

```bash
docker compose -f docker-compose.prod.yml restart app worker
```

---

## Troubleshooting

### Проблема: API не відповідає

```bash
# Перевірте логи
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker logs erpmax_orchestrator --tail 100'

# Перевірте статус контейнерів
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml ps'

# Перезапустіть
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml restart app'
```

### Проблема: Міграції не виконуються

```bash
# Перегляньте логи міграцій
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker logs erpmax_migration'

# Запустіть міграції вручну
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml run --rm migration alembic upgrade head'
```

### Проблема: База даних не запускається

```bash
# Перевірте логи PostgreSQL
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker logs erpmax_postgres'

# Перевірте доступний простір
ssh feras1960@192.168.0.83 'df -h'

# Перезапустіть PostgreSQL
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml restart postgres'
```

### Проблема: Недостатньо пам'яті

```bash
# Перевірте використання пам'яті
ssh feras1960@192.168.0.83 'free -h'

# Перевірте використання Docker
ssh feras1960@192.168.0.83 'docker stats --no-stream'

# Зменшіть кількість workers у docker-compose.prod.yml
# Змініть: --workers 4 на --workers 2
```

---

## Моніторинг

### Перевірка здоров'я системи

```bash
# API health
curl http://192.168.0.83:8000/health

# Статус контейнерів
ssh feras1960@192.168.0.83 'docker ps'

# Використання ресурсів
ssh feras1960@192.168.0.83 'docker stats --no-stream'
```

### Налаштування автоматичного моніторингу

Можна налаштувати cron job для перевірки здоров'я:

```bash
# На сервері
crontab -e

# Додайте:
*/5 * * * * curl -f http://localhost:8000/health || echo "API is down!" | mail -s "ERPMax Alert" your@email.com
```

---

## Безпека

### Рекомендації

1. **Firewall**: Налаштуйте UFW для обмеження доступу

   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 8000/tcp
   sudo ufw enable
   ```

2. **SSL/TLS**: Використовуйте Nginx або Caddy як reverse proxy з SSL

3. **Регулярні backup**: Налаштуйте автоматичні backup бази даних

4. **Оновлення**: Регулярно оновлюйте Docker образи та систему

5. **Паролі**: Ніколи не комітьте `.env.production` в git

---

## Контакти та підтримка

Для додаткової інформації дивіться:

- `README.md` - Загальна інформація
- `docs/DEPLOYMENT_GUIDE.md` - Детальний гайд з розгортання
- `docs/BILLING.md` - Інформація про біллінг
