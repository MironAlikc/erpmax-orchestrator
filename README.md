# ERPMax Orchestrator

FastAPI backend для ERPMax SaaS системи — multi-tenancy, аутентифікація, підписки та інтеграція з ERPNext.

## Технології

- **Python 3.12+**
- **FastAPI** — async web framework
- **PostgreSQL** — основна база даних
- **SQLAlchemy 2.0** — async ORM
- **Alembic** — міграції БД
- **Redis** — кешування та сесії
- **RabbitMQ** — асинхронні задачі
- **JWT** — аутентифікація

## Швидкий старт

### 1. Клонувати репозиторій

```bash
git clone <repository-url>
cd erpmax-orchestrator
```

### 2. Налаштувати середовище

```bash
# Створити .env файл з прикладу
cp .env.example .env

# Відредагувати .env та встановити SECRET_KEY
# Згенерувати SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Запустити інфраструктуру (PostgreSQL, Redis, RabbitMQ)

```bash
docker-compose up -d
```

### 4. Встановити залежності

```bash
# Створити віртуальне середовище
python -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows

# Встановити пакети
pip install -r requirements.txt
```

### 5. Запустити міграції

```bash
# Створити початкову міграцію (якщо потрібно)
alembic revision --autogenerate -m "Initial migration"

# Застосувати міграції
alembic upgrade head
```

### 6. Запустити сервер

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Структура проекту

```plaintext
erpmax-orchestrator/
├── app/
│   ├── api/          # API endpoints (routers)
│   ├── core/         # Config, database, security
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── main.py       # FastAPI application
├── alembic/          # Database migrations
├── tests/            # Tests
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Міграції БД

```bash
# Створити нову міграцію
alembic revision --autogenerate -m "Description"

# Застосувати міграції
alembic upgrade head

# Відкотити останню міграцію
alembic downgrade -1

# Переглянути історію
alembic history
```

## Docker

### Запуск тільки інфраструктури (рекомендовано для розробки)

```bash
docker-compose up -d postgres redis rabbitmq
```

### Запуск всього в Docker

```bash
# Розкоментувати секцію 'app' в docker-compose.yml
docker-compose up --build
```

### Доступ до сервісів

- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`
- **RabbitMQ Management**: <http://localhost:15672> (erpmax / erpmax_dev_password)
- **API**: <http://localhost:8000>

## API Documentation

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

## Тестування

```bash
# Запустити всі тести
pytest

# З покриттям
pytest --cov=app tests/

# Конкретний тест
pytest tests/test_auth.py -v
```

## Розгортання на продакшн

### Швидкий старт

```bash
# 1. Створити production env файл
cp .env.production.example .env.production
# Відредагувати та встановити всі паролі

# 2. Запустити з автоматичними міграціями
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 3. Перевірити статус
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

### Тестування міграцій перед deployment

```bash
# Запустити тести міграцій
./scripts/test-migrations.sh
```

### Детальна інструкція

Дивіться [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) для:

- Стратегії міграцій
- Zero-downtime deployment
- Rollback процедури
- Troubleshooting
- CI/CD integration

## Ліцензія

Proprietary
