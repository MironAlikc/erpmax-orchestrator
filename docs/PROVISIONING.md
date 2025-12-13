# Provisioning Service & API

## Purpose

Provisioning adds background jobs for ERPNext site lifecycle operations.

- create site
- delete site
- backup site

The implementation uses:

- async SQLAlchemy models for persistence
- RabbitMQ queue for background execution
- a worker process that consumes messages and updates job + tenant status

---

## Components

### Service

- `app/services/provisioning.py`
- `ProvisioningService`

Responsibilities:

- create provisioning job
- list and fetch jobs
- retry job
- cancel job
- publish job message to RabbitMQ

### API router

- `app/api/v1/provisioning.py`
- Mounted under `/api/v1/provisioning`

### RabbitMQ helper

- `app/core/rabbitmq.py`

Provides:

- `get_rabbitmq_url()`
- `publish_json(queue_name, message)`

### Worker

- `app/workers/provisioning.py`
- Run command (matches `docker-compose.prod.yml`):

```bash
python -m app.workers.provisioning
```

---

## Data model

### ProvisioningJob

- Table: `provisioning_jobs`
- Model: `app/models/provisioning.py`

Key fields:

- `tenant_id` (FK)
- `job_type` (`JobType`)
- `status` (`JobStatus`)
- `progress` (0..100)
- `message`, `error`
- `started_at`, `completed_at`, `created_at`

Enums:

- `JobStatus`: `pending`, `running`, `completed`, `failed`
- `JobType`: `create_site`, `delete_site`, `backup_site`

---

## Queue contract

Queue name:

- `Settings.provisioning_queue_name` (default: `erpmax.provisioning`)

Message payload (JSON):

```json
{
  "job_id": "<uuid>"
}
```

---

## API Endpoints

### Create job

- `POST /api/v1/provisioning/jobs`
- Access: `owner` or `admin`

Body:

```json
{
  "job_type": "create_site"
}
```

Response:

- `SingleResponse[ProvisioningJobResponse]`

### List jobs

- `GET /api/v1/provisioning/jobs`
- Access: authenticated user with tenant access
- Pagination: `page`, `size`

Response:

- `ListResponse[ProvisioningJobResponse]`

### Get job by id

- `GET /api/v1/provisioning/jobs/{job_id}`
- Access: authenticated user with tenant access

### Retry job

- `POST /api/v1/provisioning/jobs/{job_id}/retry`
- Access: `owner` or `admin`

Notes:

- allowed only for `failed` or `completed` jobs

### Cancel job

- `POST /api/v1/provisioning/jobs/{job_id}/cancel`
- Access: `owner` or `admin`

---

## Worker behavior (current MVP)

The worker performs a minimal workflow:

- set job status to `running`
- update progress
- set job status to `completed` (or `failed` on exception)
- for `create_site`:
  - set tenant status to `provisioning` when started
  - set tenant status to `active` on completion

---

## Configuration

### Environment variables

Recommended variables:

- `RABBITMQ_URL` (preferred)
- or `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`
- `PROVISIONING_QUEUE_NAME` (optional)

Notes:

- `Settings` uses `extra="ignore"`, so the preferred way is to set env vars matching the field names:
  - `rabbitmq_url`
  - `provisioning_queue_name`

---

## Local verification

1) Start dependencies (Postgres, RabbitMQ)
2) Run API
3) Create a job via Swagger:

- `http://127.0.0.1:8000/docs`

1) Run worker:

```bash
python -m app.workers.provisioning
```

---

## Limitations / Next steps

- Worker currently simulates provisioning; ERPNext/Frappe integration should be added.
- Add idempotency and stronger validation for messages.
- Add structured logging, metrics, and dead-letter queue strategy.
- Add real cancellation semantics (currently marks job as failed).
