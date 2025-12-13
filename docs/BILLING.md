# Billing Service & API

- керування тарифними планами (`Plan`)
- отримання поточної підписки тенанта (`Subscription`)
- ініціація checkout-сесії для оплати/зміни плану (Stripe)
- скасування підписки (в т.ч. через Stripe)
- прийом webhook-подій Stripe і запис платіжних подій (`PaymentEvent`)

> Примітка: інтеграція зроблена як мінімально життєздатний варіант (MVP). Повний цикл Stripe Billing (Products/Prices, proration, trial management, invoices API) може бути розширений у наступних ітераціях.

---

## Реалізовані компоненти

### 1) API роутер

- Файл: `app/api/v1/billing.py`
- Префікс: `/api/v1/billing`

### 2) Бізнес-логіка

- Файл: `app/services/billing.py`
- Клас: `BillingService`

### 3) Stripe інтеграція (MVP)

- Файл: `app/services/stripe.py`
- Клас: `StripeService`
- Використовується `httpx` (без SDK `stripe`), щоб мінімізувати залежності.

### 4) Конфігурація

- Файл: `app/core/config.py`
- Додані поля налаштувань:
  - `stripe_secret_key`
  - `stripe_webhook_secret`
  - `liqpay_public_key`
  - `liqpay_private_key`

---

## Моделі та зберігання даних

### Plan

- Таблиця: `plans`
- Ключові поля:
  - `slug`, `price_monthly`, `price_yearly`, `currency`, `is_active`, `limits`, `features`

### Subscription

- Таблиця: `subscriptions`
- Важливі поля для інтеграції з провайдером:
  - `payment_provider` (наприклад `stripe`)
  - `external_customer_id`
  - `external_subscription_id`

### PaymentEvent

- Таблиця: `payment_events`
- Призначення: зберігання історії подій (успіх/помилка/рефанд/чарджбек) з провайдера.

---

## Endpoints

### 1) Список планів

- Метод: `GET /api/v1/billing/plans`
- Доступ: public (без авторизації)
- Опис: повертає активні плани, відсортовані по `sort_order`.

### 2) Поточна підписка

- Метод: `GET /api/v1/billing/subscription`
- Доступ: потрібен `Authorization: Bearer <access_token>`
- Опис: повертає поточну підписку тенанта + вкладений план (`plan`).

### 3) Checkout-сесія

- Метод: `POST /api/v1/billing/checkout`
- Доступ: потрібен `Authorization: Bearer <access_token>`
- Тіло: `CheckoutRequest`
  - `plan_id`
  - `billing_period`
  - `payment_provider` (зараз підтримується лише `stripe`)
  - `success_url`
  - `cancel_url`
- Результат: `CheckoutResponse` (`checkout_url`, `session_id`).

### 4) Скасування підписки

- Метод: `POST /api/v1/billing/cancel`
- Доступ: `owner only` (RBAC)
- Тіло: `CancelSubscriptionRequest`
  - `reason` (optional)
  - `cancel_at_period_end` (default `true`)

### 5) Історія платежів (payment events)

- Метод: `GET /api/v1/billing/invoices`
- Доступ: потрібен `Authorization: Bearer <access_token>`
- Пагінація: стандартна через `Pagination` (`page`, `size`).
- Опис: повертає список `PaymentEvent` для підписки поточного тенанта.

### 6) Stripe Webhook

- Метод: `POST /api/v1/billing/webhook/stripe`
- Заголовок: `Stripe-Signature`
- Опис:
  - валідація підпису на основі `STRIPE_WEBHOOK_SECRET`
  - парсинг payload
  - прив’язка події до `tenant_id` через `metadata.tenant_id`
  - створення `PaymentEvent` (якщо `provider_event_id` ще не існує)
  - оновлення `Subscription.status` для подій типу `invoice.paid` / `invoice.payment_failed`

> Рекомендація: у production бажано додати rate-limiting, idempotency та окремі журнали аудиту.

---

## Stripe флоу (MVP)

### 1) Checkout

- `BillingService.create_checkout()`:
  - перевіряє, що `payment_provider == "stripe"`
  - знаходить `Plan`
  - знаходить поточну `Subscription`
  - створює customer у Stripe (якщо `external_customer_id` відсутній)
  - створює checkout session
  - зберігає `subscription.payment_provider = "stripe"` та `external_customer_id`

### 2) Webhook

- `BillingService.handle_stripe_webhook()`:
  - перевіряє підпис `Stripe-Signature`
  - читає `tenant_id` з `metadata.tenant_id`
  - знаходить `Subscription` по `tenant_id`
  - записує `PaymentEvent` (idempotent за `provider_event_id`)
  - оновлює статус підписки:
    - `invoice.paid` / `checkout.session.completed` -> `ACTIVE`
    - `invoice.payment_failed` -> `PAST_DUE`

---

## Змінні оточення (env)

### Development

- Файл: `.env.example`

Потрібні значення для Stripe:

- `STRIPE_SECRET_KEY=sk_test_...`
- `STRIPE_WEBHOOK_SECRET=whsec_...`

### Production

- Файл: `.env.production.example`

---

## Тести

Додано smoke-тести для Billing API:

- `tests/test_billing_api.py`
  - використовує `dependency_overrides` FastAPI
  - не потребує реальної БД

Додатково:

- `tests/test_db_connection.py` тепер робить `skip`, якщо Postgres недоступний на `localhost:5432` (щоб тести не падали у середовищах без БД).

Запуск тестів:

```bash
python -m pytest -q
```

---

## Відомі обмеження / TODO

- Підтримується лише `stripe` як `payment_provider` (LiqPay — тільки конфіг поля).
- У Stripe checkout використовується `price_data` напряму (без Stripe Products/Prices).
- Webhook-обробка мінімальна (частина типів подій не мапиться).
- Немає повного інвойс-менеджменту через Stripe API (отримання pdf, hosted invoice url, тощо).
- Немає token blacklist / logout invalidation (це окрема задача).

---

## Зміни в інших модулях

- `app/services/tenant.py`:
  - виправлено завантаження підписки: `selectinload(Tenant.subscription)` замість неіснуючого `Tenant.subscriptions`
  - додано eager-load `Subscription.plan`

---

## Як перевірити вручну (локально)

1) Запустити API
1) Відкрити Swagger:

- `http://127.0.0.1:8000/docs`

1) Перевірити endpoints:

- `GET /api/v1/billing/plans`
- `GET /api/v1/billing/subscription` (потрібен `access_token`)

---

## Статус

Реалізовано для development MVP і покрита smoke-тестами.
