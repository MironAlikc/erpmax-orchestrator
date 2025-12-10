# Deployment Guide — ERPMax Orchestrator

## Стратегія міграцій

### Проблема

Застосування міграцій безпосередньо на продакшн сервері може призвести до:

- Downtime під час міграції
- Конфлікти при одночасному запуску кількох інстансів
- Відсутність rollback стратегії
- Ризик втрати даних

### Рішення

Використовуємо **окремий migration service** в Docker Compose, який:

- Запускається **перед** основним додатком
- Виконує міграції **один раз**
- Завершується після успішного виконання
- Блокує запуск додатку до завершення міграцій

---

## Архітектура

```
┌─────────────────┐
│   PostgreSQL    │
└────────┬────────┘
         │
         ↓ (wait for healthy)
┌─────────────────┐
│   Migration     │ ← Runs alembic upgrade head
│   Container     │   (restart: no)
└────────┬────────┘
         │
         ↓ (depends_on: service_completed_successfully)
┌─────────────────┐
│   App           │ ← Starts only after migration
│   Container     │   (restart: unless-stopped)
└─────────────────┘
```

---

## Файли

### 1. `docker-entrypoint.sh`

Entrypoint скрипт для контейнерів:

- Чекає на готовність PostgreSQL
- Опціонально запускає міграції (якщо `RUN_MIGRATIONS=true`)
- Запускає основний додаток

### 2. `docker-compose.prod.yml`

Production-ready конфігурація з:

- **migration service** — окремий контейнер для міграцій
- **app service** — основний додаток (залежить від migration)
- **worker service** — background tasks (також залежить від migration)
- Health checks для всіх сервісів
- Restart policies
- Networks ізоляція

### 3. `.env.production.example`

Шаблон для production змінних оточення

---

## Локальна розробка

### Запуск

```bash
# Використовуємо звичайний docker-compose.yml
docker compose up -d postgres redis rabbitmq

# Міграції вручну
alembic upgrade head

# Запуск додатку
uvicorn app.main:app --reload
```

---

## Production Deployment

### Підготовка

1. **Створити `.env.production`**

```bash
cp .env.production.example .env.production
# Відредагувати та встановити всі паролі
```

2. **Згенерувати SECRET_KEY**

```bash
openssl rand -hex 32
```

### Перший запуск

```bash
# Запустити всі сервіси
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# Перевірити логи міграції
docker logs erpmax_migration

# Перевірити статус
docker compose -f docker-compose.prod.yml ps
```

### Оновлення з новими міграціями

```bash
# 1. Зупинити додаток (але не БД!)
docker compose -f docker-compose.prod.yml stop app worker

# 2. Оновити код
git pull origin main

# 3. Перебудувати образи
docker compose -f docker-compose.prod.yml build

# 4. Запустити міграцію
docker compose -f docker-compose.prod.yml up migration

# 5. Перевірити логи
docker logs erpmax_migration

# 6. Якщо успішно — запустити додаток
docker compose -f docker-compose.prod.yml up -d app worker

# 7. Перевірити здоров'я
curl http://localhost:8000/health
```

### Rollback міграції

```bash
# Зайти в migration контейнер
docker compose -f docker-compose.prod.yml run --rm migration bash

# Відкотити на 1 версію назад
alembic downgrade -1

# Або на конкретну версію
alembic downgrade <revision_id>

# Перезапустити додаток
docker compose -f docker-compose.prod.yml restart app worker
```

---

## Zero-Downtime Deployment

Для zero-downtime потрібна більш складна стратегія:

### Варіант 1: Blue-Green Deployment

```bash
# 1. Запустити нову версію на іншому порті
docker compose -f docker-compose.prod.yml \
  -p erpmax-green \
  --env-file .env.production \
  up -d

# 2. Перевірити здоров'я
curl http://localhost:8001/health

# 3. Переключити load balancer на новий порт

# 4. Зупинити стару версію
docker compose -f docker-compose.prod.yml \
  -p erpmax-blue \
  down
```

### Варіант 2: Rolling Update з Kubernetes

Для production краще використовувати Kubernetes з:

- Init containers для міграцій
- Rolling updates
- Health checks
- Auto-scaling

---

## Моніторинг міграцій

### Перевірка поточної версії БД

```bash
# Через Docker
docker compose -f docker-compose.prod.yml run --rm migration alembic current

# Або через psql
docker exec -it erpmax_postgres psql -U erpmax -d erpmax_orchestrator \
  -c "SELECT version_num FROM alembic_version;"
```

### Історія міграцій

```bash
docker compose -f docker-compose.prod.yml run --rm migration alembic history
```

### Перевірка pending міграцій

```bash
# Показати, які міграції ще не застосовані
docker compose -f docker-compose.prod.yml run --rm migration \
  alembic current
```

---

## Best Practices

### DO

1. **Завжди тестуйте міграції локально**

   ```bash
   # Створити тестову БД
   docker compose up -d postgres
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```

2. **Робіть backup перед міграцією**

   ```bash
   docker exec erpmax_postgres pg_dump -U erpmax erpmax_orchestrator > backup.sql
   ```

3. **Використовуйте транзакції в міграціях**
   - Alembic автоматично обгортає міграції в транзакції

4. **Пишіть reversible міграції**
   - Завжди реалізуйте `downgrade()` функцію

5. **Тестуйте на staging перед production**

### DON'T

1. **Не запускайте міграції вручну на production**
   - Використовуйте migration service

2. **Не видаляйте старі міграції**
   - Це порушить історію

3. **Не змінюйте вже застосовані міграції**
   - Створюйте нову міграцію для виправлень

4. **Не запускайте кілька міграцій одночасно**
   - Docker Compose гарантує один migration container

---

## Troubleshooting

### Міграція зависла

```bash
# Перевірити логи
docker logs erpmax_migration

# Перевірити lock в БД
docker exec -it erpmax_postgres psql -U erpmax -d erpmax_orchestrator \
  -c "SELECT * FROM pg_locks WHERE NOT granted;"

# Якщо потрібно — kill процес
docker compose -f docker-compose.prod.yml stop migration
```

### Міграція failed

```bash
# Перевірити помилку
docker logs erpmax_migration

# Відкотити вручну
docker compose -f docker-compose.prod.yml run --rm migration alembic downgrade -1

# Виправити міграцію та повторити
docker compose -f docker-compose.prod.yml up migration
```

### Додаток не стартує після міграції

```bash
# Перевірити статус міграції
docker compose -f docker-compose.prod.yml ps migration

# Якщо migration failed — додаток не запуститься через depends_on
# Виправити міграцію та перезапустити
```

---

## CI/CD Integration

### GitHub Actions приклад

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build images
        run: docker compose -f docker-compose.prod.yml build
      
      - name: Run migrations
        run: docker compose -f docker-compose.prod.yml up migration
      
      - name: Deploy app
        run: docker compose -f docker-compose.prod.yml up -d app worker
```

---

## Висновок

**Migration service** забезпечує:

- Безпечне застосування міграцій
- Правильний порядок запуску сервісів
- Можливість rollback
- Ізоляцію міграцій від основного додатку

**Production-ready** конфігурація включає:

- Health checks
- Restart policies
- Secrets через environment variables
- Network isolation
- Proper dependencies
