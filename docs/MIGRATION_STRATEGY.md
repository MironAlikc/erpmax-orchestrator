# Migration Strategy — Production Ready

## Проблема

При застосуванні міграцій на продакшн сервері можуть виникнути:

### Потенційні проблеми

1. **Race Condition** — кілька інстансів додатку одночасно запускають міграції
2. **Downtime** — додаток недоступний під час міграції
3. **Data Loss** — помилка в міграції може призвести до втрати даних
4. **Rollback складність** — важко відкотити зміни
5. **Lock conflicts** — міграція блокує таблиці

---

## Рішення

### Архітектура

```
┌──────────────────────────────────────────────────┐
│  docker-compose.prod.yml                         │
├──────────────────────────────────────────────────┤
│                                                  │
│  1. postgres (healthcheck)                       │
│     └─> ready                                    │
│                                                  │
│  2. migration (depends_on: postgres healthy)     │
│     └─> alembic upgrade head                     │
│     └─> exit (restart: no)                       │
│                                                  │
│  3. app (depends_on: migration completed)        │
│     └─> uvicorn app.main:app                     │
│     └─> restart: unless-stopped                  │
│                                                  │
│  4. worker (depends_on: migration completed)     │
│     └─> python -m app.workers.provisioning       │
│     └─> restart: unless-stopped                  │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Ключові особливості

#### 1. Окремий Migration Service

```yaml
migration:
  build: .
  command: alembic upgrade head
  restart: "no"  # ← Запускається один раз
  depends_on:
    postgres:
      condition: service_healthy
```

**Переваги:**

- Гарантовано один запуск міграції
- Не блокує основний додаток
- Легко перевірити логи: `docker logs erpmax_migration`

#### 2. Service Dependencies

```yaml
app:
  depends_on:
    migration:
      condition: service_completed_successfully  # ← Чекає завершення
```

**Переваги:**

- Додаток не запуститься, якщо міграція failed
- Правильний порядок запуску
- Безпечний deployment

#### 3. Health Checks

```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U erpmax"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Переваги:**

- Міграція чекає готовності БД
- Уникає connection errors
- Автоматичний retry

---

## Workflow

### Перший Deploy

```bash
# 1. Підготовка
cp .env.production.example .env.production
# Встановити всі паролі та SECRET_KEY

# 2. Запуск
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# Що відбувається:
# ├─ postgres стартує
# ├─ postgres стає healthy
# ├─ migration запускається
# ├─ alembic upgrade head виконується
# ├─ migration завершується (exit 0)
# ├─ app запускається
# └─ worker запускається

# 3. Перевірка
docker compose -f docker-compose.prod.yml ps
docker logs erpmax_migration
curl http://localhost:8000/health
```

### Update з новими міграціями

```bash
# 1. Зупинити додаток (БД залишається)
docker compose -f docker-compose.prod.yml stop app worker

# 2. Оновити код
git pull origin main

# 3. Перебудувати образи
docker compose -f docker-compose.prod.yml build

# 4. Запустити міграцію
docker compose -f docker-compose.prod.yml up migration

# 5. Перевірити результат
docker logs erpmax_migration
# Якщо exit code = 0 → успішно

# 6. Запустити додаток
docker compose -f docker-compose.prod.yml up -d app worker
```

### Rollback

```bash
# Варіант 1: Через migration container
docker compose -f docker-compose.prod.yml run --rm migration alembic downgrade -1

# Варіант 2: Відновлення з backup
docker exec -i erpmax_postgres psql -U erpmax -d erpmax_orchestrator < backup.sql

# Перезапустити додаток
docker compose -f docker-compose.prod.yml restart app worker
```

---

## Безпека

### 1. Backup перед міграцією

```bash
# Автоматичний backup скрипт
cat > scripts/backup-before-migration.sh << 'EOF'
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backups/db_backup_${TIMESTAMP}.sql"

mkdir -p backups
docker exec erpmax_postgres pg_dump -U erpmax erpmax_orchestrator > $BACKUP_FILE
echo "Backup created: $BACKUP_FILE"
EOF

chmod +x scripts/backup-before-migration.sh
```

### 2. Тестування локально

```bash
# Запустити тести міграцій
./scripts/test-migrations.sh

# Тести включають:
# Fresh migration
# Downgrade
# Re-upgrade
# Table verification
# Connection test
```

### 3. Staging Environment

```bash
# Спочатку на staging
docker compose -f docker-compose.prod.yml \
  --env-file .env.staging \
  up -d

# Перевірити
# Якщо OK → deploy на production
```

---

## Моніторинг

### Перевірка статусу міграції

```bash
# Поточна версія БД
docker compose -f docker-compose.prod.yml run --rm migration alembic current

# Історія міграцій
docker compose -f docker-compose.prod.yml run --rm migration alembic history

# Pending міграції
docker compose -f docker-compose.prod.yml run --rm migration alembic heads
```

### Логи

```bash
# Migration logs
docker logs erpmax_migration

# App logs
docker logs erpmax_orchestrator

# Всі логи разом
docker compose -f docker-compose.prod.yml logs -f
```

---

## Troubleshooting

### Міграція failed

```bash
# 1. Перевірити помилку
docker logs erpmax_migration

# 2. Перевірити БД
docker exec -it erpmax_postgres psql -U erpmax -d erpmax_orchestrator

# 3. Відкотити
docker compose -f docker-compose.prod.yml run --rm migration alembic downgrade -1

# 4. Виправити міграцію в коді

# 5. Повторити
docker compose -f docker-compose.prod.yml up migration
```

### Додаток не стартує

```bash
# Перевірити статус migration
docker compose -f docker-compose.prod.yml ps migration

# Якщо migration failed → app не запуститься
# Виправити міграцію та перезапустити
```

### Lock в БД

```bash
# Перевірити locks
docker exec -it erpmax_postgres psql -U erpmax -d erpmax_orchestrator \
  -c "SELECT * FROM pg_locks WHERE NOT granted;"

# Kill процес якщо потрібно
docker compose -f docker-compose.prod.yml stop migration
```

---

## Best Practices

### DO

1. **Завжди робіть backup**

   ```bash
   ./scripts/backup-before-migration.sh
   ```

2. **Тестуйте локально**

   ```bash
   ./scripts/test-migrations.sh
   ```

3. **Використовуйте staging**
   - Спочатку на staging
   - Потім на production

4. **Пишіть reversible міграції**
   - Завжди реалізуйте `downgrade()`

5. **Моніторте логи**

   ```bash
   docker logs -f erpmax_migration
   ```

### DON'T

1. **Не запускайте міграції вручну на production**
   - Використовуйте migration service

2. **Не видаляйте старі міграції**
   - Порушує історію

3. **Не змінюйте застосовані міграції**
   - Створюйте нову для виправлень

4. **Не ігноруйте failed migrations**
   - Додаток не запуститься через depends_on

---

Детальніше: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
Billing service implementation details: [BILLING.md](BILLING.md)
