# Швидкі команди для розгортання

## 🚀 Перше розгортання

```bash
./deploy.sh
```

## 🔄 Оновлення додатка

```bash
./update.sh
```

## 📋 Швидкі SSH команди

### Підключення до сервера

```bash
ssh feras1960@192.168.0.83
```

### Перегляд логів

```bash
# Всі логи
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml logs -f'

# Тільки додаток
ssh feras1960@192.168.0.83 'docker logs -f erpmax_orchestrator'

# Останні 50 рядків
ssh feras1960@192.168.0.83 'docker logs erpmax_orchestrator --tail 50'
```

### Статус сервісів

```bash
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml ps'
```

### Перезапуск

```bash
# Перезапустити додаток
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml restart app'

# Перезапустити все
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml restart'
```

### Зупинка

```bash
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml down'
```

### Запуск

```bash
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml up -d'
```

## 🏥 Перевірка здоров'я

```bash
curl http://192.168.0.83:8000/health
```

## 🌐 URL адреси

- **API**: <http://192.168.0.83:8000>
- **Документація**: <http://192.168.0.83:8000/docs>
- **ReDoc**: <http://192.168.0.83:8000/redoc>

## 💾 Backup

```bash
# Створити backup
ssh feras1960@192.168.0.83 'docker exec erpmax_postgres pg_dump -U erpmax erpmax_orchestrator > ~/backup_$(date +%Y%m%d_%H%M%S).sql'

# Завантажити backup
scp feras1960@192.168.0.83:~/backup_*.sql ./backups/
```

## 🔧 Налаштування

```bash
# Редагувати .env.production
ssh feras1960@192.168.0.83 'nano /home/feras1960/erpmax-orchestrator/.env.production'

# Після змін перезапустити
ssh feras1960@192.168.0.83 'cd /home/feras1960/erpmax-orchestrator && docker compose -f docker-compose.prod.yml restart app worker'
```
