from enum import Enum


class TenantStatus(str, Enum):
    """Tenant status enum"""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class TenantRole(str, Enum):
    """User role within a tenant"""

    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"


class SubscriptionStatus(str, Enum):
    """Subscription status enum"""

    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class BillingPeriod(str, Enum):
    """Billing period enum"""

    MONTHLY = "monthly"
    YEARLY = "yearly"


class PaymentEventType(str, Enum):
    """Payment event type enum"""

    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    REFUND = "refund"
    CHARGEBACK = "chargeback"


class JobStatus(str, Enum):
    """Provisioning job status enum"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    """Provisioning job type enum"""

    CREATE_SITE = "create_site"
    DELETE_SITE = "delete_site"
    BACKUP_SITE = "backup_site"
