# ERPMax Orchestrator

FastAPI backend для ERPMax SaaS системи.

## Технології

- Python 3.12+
- FastAPI
- PostgreSQL
- SQLAlchemy (async)
- RabbitMQ
- Redis

## Локальний запуск
```bash
# Створити віртуальне середовище
python -m venv venv
source venv/bin/activate

# Встановити залежності
pip install -r requirements.txt

# Запустити
uvicorn app.main:app --reload
```

## Docker
```bash
docker build -t erpmax-orchestrator .
docker run -p 8000:8000 erpmax-orchestrator
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
