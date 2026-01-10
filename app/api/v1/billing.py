"""Billing endpoints"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_current_tenant,
    require_role,
    Pagination,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.models import Tenant, User
from app.models.enums import TenantRole
from app.schemas.base import SingleResponse, ListResponse, MessageResponse
from app.schemas.plan import PlanResponse
from app.schemas.subscription import (
    SubscriptionWithPlan,
    CheckoutRequest,
    CheckoutResponse,
    CancelSubscriptionRequest,
    PaymentEventResponse,
)
from app.services.billing import BillingService


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/plans",
    response_model=ListResponse[PlanResponse],
    summary="List available plans",
    description="List active subscription plans.",
)
async def list_plans(
    db: AsyncSession = Depends(get_db),
):
    try:
        billing_service = BillingService(db)
        plans = await billing_service.list_active_plans()
        data = [PlanResponse.model_validate(p) for p in plans]

        return ListResponse(status="success", data=data, pagination=None)

    except Exception as e:
        logger.error(f"List plans error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list plans",
        )


@router.get(
    "/subscription",
    response_model=SingleResponse[SubscriptionWithPlan],
    summary="Get current subscription",
    description="Get current tenant subscription with plan details.",
)
async def get_subscription(
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        billing_service = BillingService(db)
        subscription = await billing_service.get_current_subscription(current_tenant.id)

        data = SubscriptionWithPlan.model_validate(subscription)

        return SingleResponse(status="success", data=data)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Get subscription error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription",
        )


@router.post(
    "/checkout",
    response_model=SingleResponse[CheckoutResponse],
    summary="Create checkout session",
    description="Create payment checkout session for plan change.",
)
async def create_checkout(
    data: CheckoutRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    logger.info(
        f"Checkout request - User: {current_user.email}, Tenant: {current_tenant.name}, "
        f"Plan: {data.plan_id}, Period: {data.billing_period}, Provider: {data.payment_provider}"
    )

    try:
        billing_service = BillingService(db)
        result = await billing_service.create_checkout(
            tenant=current_tenant,
            user=current_user,
            plan_id=data.plan_id,
            billing_period=data.billing_period,
            payment_provider=data.payment_provider,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )

        response_data = CheckoutResponse(**result)
        logger.info(
            f"Checkout session created successfully for tenant: {current_tenant.name}"
        )
        return SingleResponse(status="success", data=response_data)

    except (NotFoundError, ValidationError) as e:
        logger.warning(
            f"Checkout validation error - Tenant: {current_tenant.name}, Error: {str(e.message)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message)
        )
    except Exception as e:
        logger.error(
            f"Create checkout error - Tenant: {current_tenant.name}, "
            f"Plan: {data.plan_id}, Error: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.post(
    "/cancel",
    response_model=SingleResponse[SubscriptionWithPlan],
    summary="Cancel subscription",
    description="Cancel current tenant subscription (owner only).",
    dependencies=[Depends(require_role(TenantRole.OWNER))],
)
async def cancel_subscription(
    data: CancelSubscriptionRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        billing_service = BillingService(db)
        subscription = await billing_service.cancel_subscription(
            tenant_id=current_tenant.id,
            reason=data.reason,
            cancel_at_period_end=data.cancel_at_period_end,
        )

        data_out = SubscriptionWithPlan.model_validate(subscription)
        return SingleResponse(status="success", data=data_out)

    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Cancel subscription error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )


@router.get(
    "/invoices",
    response_model=ListResponse[PaymentEventResponse],
    summary="List payment events",
    description="List payment events for current tenant subscription.",
)
async def list_invoices(
    current_tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db),
):
    try:
        billing_service = BillingService(db)
        events, total = await billing_service.list_payment_events(
            tenant_id=current_tenant.id,
            limit=pagination.limit,
            offset=pagination.skip,
        )

        data_out = [PaymentEventResponse.model_validate(e) for e in events]

        return ListResponse(
            status="success",
            data=data_out,
            pagination=pagination.get_pagination_info(total),
        )

    except Exception as e:
        logger.error(f"List invoices error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list payment events",
        )


@router.post(
    "/webhook/stripe",
    response_model=MessageResponse,
    summary="Stripe webhook",
    description="Handle Stripe webhooks.",
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header("", alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await request.body()
        billing_service = BillingService(db)
        await billing_service.handle_stripe_webhook(
            payload=payload,
            signature_header=stripe_signature,
        )

        return MessageResponse(status="success", message="Webhook received")

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )
