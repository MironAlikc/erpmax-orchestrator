"""
Script to create test users (regular user and admin) for development/testing
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_db
from app.models import User, Tenant, UserTenant, Subscription, Plan
from app.models.enums import TenantRole, TenantStatus, SubscriptionStatus, BillingPeriod
from app.core.security import hash_password
from sqlalchemy import select
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_test_users():
    """Create test users in database"""
    async for db in get_db():
        try:
            # Check if users already exist
            result = await db.execute(
                select(User).where(
                    User.email.in_(["test@example.com", "admin@example.com"])
                )
            )
            existing_users = result.scalars().all()

            if existing_users:
                logger.info("Users already exist. Deleting old users first...")
                for user in existing_users:
                    await db.delete(user)
                await db.commit()

            # Get or create trial plan
            result = await db.execute(select(Plan).where(Plan.slug == "trial"))
            trial_plan = result.scalar_one_or_none()

            if not trial_plan:
                logger.info("Creating trial plan...")
                trial_plan = Plan(
                    name="Trial",
                    slug="trial",
                    description="14-day free trial",
                    price_monthly=0,
                    price_yearly=0,
                    currency="USD",
                    limits={"users": 3, "storage_gb": 10},
                    features=["Basic features", "Email support"],
                    is_active=True,
                    sort_order=0,
                )
                db.add(trial_plan)
                await db.flush()

            # Create test user
            logger.info("Creating test user...")
            test_user = User(
                email="test@example.com",
                full_name="Test User",
                hashed_password=hash_password("password"),
                is_active=True,
                is_superuser=False,
            )
            db.add(test_user)
            await db.flush()

            # Create tenant for test user
            test_tenant = Tenant(
                name="Test Company",
                slug="test-company",
                status=TenantStatus.ACTIVE,
            )
            db.add(test_tenant)
            await db.flush()

            # Link user to tenant
            test_user_tenant = UserTenant(
                user_id=test_user.id,
                tenant_id=test_tenant.id,
                role=TenantRole.OWNER,
                is_default=True,
            )
            db.add(test_user_tenant)

            # Create subscription for test tenant
            test_subscription = Subscription(
                tenant_id=test_tenant.id,
                plan_id=trial_plan.id,
                status=SubscriptionStatus.TRIAL,
                billing_period=BillingPeriod.MONTHLY,
                trial_ends_at=datetime.utcnow() + timedelta(days=14),
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=14),
            )
            db.add(test_subscription)

            # Create admin user
            logger.info("Creating admin user...")
            admin_user = User(
                email="admin@example.com",
                full_name="Admin User",
                hashed_password=hash_password("admin123"),
                is_active=True,
                is_superuser=True,
            )
            db.add(admin_user)
            await db.flush()

            # Create tenant for admin
            admin_tenant = Tenant(
                name="Admin Company",
                slug="admin-company",
                status=TenantStatus.ACTIVE,
            )
            db.add(admin_tenant)
            await db.flush()

            # Link admin to tenant
            admin_user_tenant = UserTenant(
                user_id=admin_user.id,
                tenant_id=admin_tenant.id,
                role=TenantRole.OWNER,
                is_default=True,
            )
            db.add(admin_user_tenant)

            # Create subscription for admin tenant
            admin_subscription = Subscription(
                tenant_id=admin_tenant.id,
                plan_id=trial_plan.id,
                status=SubscriptionStatus.ACTIVE,
                billing_period=BillingPeriod.MONTHLY,
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=365),
            )
            db.add(admin_subscription)

            # Commit all changes
            await db.commit()

            logger.info("\n✅ Test users created successfully!")
            logger.info("\nTest User:")
            logger.info(f"  Email: test@example.com")
            logger.info(f"  Password: password")
            logger.info(f"  Tenant: Test Company")
            logger.info(f"  Role: Owner")

            logger.info("\nAdmin User:")
            logger.info(f"  Email: admin@example.com")
            logger.info(f"  Password: admin123")
            logger.info(f"  Tenant: Admin Company")
            logger.info(f"  Role: Owner (Superuser)")

        except Exception as e:
            logger.error(f"❌ Error creating test users: {str(e)}")
            await db.rollback()
            raise
        finally:
            break


if __name__ == "__main__":
    asyncio.run(create_test_users())
