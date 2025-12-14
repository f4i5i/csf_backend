"""User endpoints for managing subscriptions."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from app.models.user import User
from app.models.enrollment import Enrollment
from app.services.subscription_service import SubscriptionService
from app.services.stripe_service import StripeService
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


# ============== Schemas ==============


class SubscriptionResponse(BaseModel):
    """Response schema for subscription details."""

    enrollment_id: str
    class_id: str
    class_name: str
    child_id: str
    child_name: str
    subscription_id: str
    subscription_status: str
    billing_amount: str
    billing_interval: str
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool
    cancelled_at: str | None

    model_config = {"from_attributes": True}


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel a subscription."""

    cancel_immediately: bool = Field(
        default=False,
        description="If true, cancel now with proration. If false, cancel at period end.",
    )


class UpdatePaymentMethodRequest(BaseModel):
    """Request to update subscription payment method."""

    payment_method_id: str = Field(..., description="New Stripe payment method ID")


# ============== Endpoints ==============


@router.get("", response_model=List[SubscriptionResponse])
async def list_user_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all active subscriptions for the current user.

    Returns subscriptions across all enrolled children.
    """
    try:
        enrollments = await Enrollment.get_active_subscriptions_by_user(
            db, current_user.id
        )

        subscriptions = []
        for enrollment in enrollments:
            # Format billing info
            class_ = enrollment.class_
            billing_amount = class_.get_subscription_price()
            billing_interval = class_.billing_model.value

            subscriptions.append(
                {
                    "enrollment_id": enrollment.id,
                    "class_id": class_.id,
                    "class_name": class_.name,
                    "child_id": enrollment.child_id,
                    "child_name": f"{enrollment.child.first_name} {enrollment.child.last_name}",
                    "subscription_id": enrollment.stripe_subscription_id,
                    "subscription_status": enrollment.subscription_status,
                    "billing_amount": str(billing_amount),
                    "billing_interval": billing_interval,
                    "current_period_start": enrollment.current_period_start.isoformat()
                    if enrollment.current_period_start
                    else None,
                    "current_period_end": enrollment.current_period_end.isoformat()
                    if enrollment.current_period_end
                    else None,
                    "cancel_at_period_end": enrollment.cancel_at_period_end,
                    "cancelled_at": enrollment.subscription_cancelled_at.isoformat()
                    if enrollment.subscription_cancelled_at
                    else None,
                }
            )

        return subscriptions

    except Exception as e:
        logger.error(f"Failed to list subscriptions for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list subscriptions",
        )


@router.get("/{enrollment_id}", response_model=SubscriptionResponse)
async def get_subscription_details(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information about a specific subscription.

    Requires user to own the enrollment.
    """
    try:
        enrollment = await Enrollment.get_by_id(db, enrollment_id)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        # Verify ownership
        if enrollment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this subscription",
            )

        if not enrollment.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found for this enrollment",
            )

        # Format response
        class_ = enrollment.class_
        billing_amount = class_.get_subscription_price()
        billing_interval = class_.billing_model.value

        return {
            "enrollment_id": enrollment.id,
            "class_id": class_.id,
            "class_name": class_.name,
            "child_id": enrollment.child_id,
            "child_name": f"{enrollment.child.first_name} {enrollment.child.last_name}",
            "subscription_id": enrollment.stripe_subscription_id,
            "subscription_status": enrollment.subscription_status,
            "billing_amount": str(billing_amount),
            "billing_interval": billing_interval,
            "current_period_start": enrollment.current_period_start.isoformat()
            if enrollment.current_period_start
            else None,
            "current_period_end": enrollment.current_period_end.isoformat()
            if enrollment.current_period_end
            else None,
            "cancel_at_period_end": enrollment.cancel_at_period_end,
            "cancelled_at": enrollment.subscription_cancelled_at.isoformat()
            if enrollment.subscription_cancelled_at
            else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get subscription details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription details",
        )


@router.post("/{enrollment_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_subscription(
    enrollment_id: str,
    data: CancelSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a subscription.

    - If cancel_immediately=false: Subscription continues until end of billing period
    - If cancel_immediately=true: Subscription cancelled now with proration refund
    """
    try:
        enrollment = await Enrollment.get_by_id(db, enrollment_id)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        # Verify ownership
        if enrollment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to cancel this subscription",
            )

        if not enrollment.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found",
            )

        # Cancel subscription
        stripe_service = StripeService()
        subscription_service = SubscriptionService(stripe_service)

        await subscription_service.cancel_subscription(
            db_session=db,
            enrollment=enrollment,
            cancel_immediately=data.cancel_immediately,
            prorate=True,  # Always prorate for user-initiated cancellations
        )

        return {
            "message": "Subscription cancelled successfully",
            "cancel_immediately": data.cancel_immediately,
            "effective_date": "end of billing period"
            if not data.cancel_immediately
            else "immediately",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )


@router.post("/{enrollment_id}/reactivate", status_code=status.HTTP_200_OK)
async def reactivate_subscription(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reactivate a subscription that was scheduled for cancellation.

    Only works for subscriptions cancelled at period end (not immediate cancellations).
    """
    try:
        enrollment = await Enrollment.get_by_id(db, enrollment_id)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        # Verify ownership
        if enrollment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to reactivate this subscription",
            )

        if not enrollment.cancel_at_period_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is not scheduled for cancellation",
            )

        # Reactivate subscription
        stripe_service = StripeService()
        subscription_service = SubscriptionService(stripe_service)

        await subscription_service.reactivate_subscription(
            db_session=db,
            enrollment=enrollment,
        )

        return {
            "message": "Subscription reactivated successfully",
            "subscription_id": enrollment.stripe_subscription_id,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reactivate subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate subscription",
        )


@router.put("/{enrollment_id}/payment-method", status_code=status.HTTP_200_OK)
async def update_payment_method(
    enrollment_id: str,
    data: UpdatePaymentMethodRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the payment method for a subscription.

    The new payment method will be used for future billing.
    """
    try:
        enrollment = await Enrollment.get_by_id(db, enrollment_id)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        # Verify ownership
        if enrollment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this subscription",
            )

        if not enrollment.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found",
            )

        # Update payment method
        stripe_service = StripeService()
        subscription_service = SubscriptionService(stripe_service)

        await subscription_service.update_payment_method(
            db_session=db,
            enrollment=enrollment,
            payment_method_id=data.payment_method_id,
        )

        return {
            "message": "Payment method updated successfully",
            "subscription_id": enrollment.stripe_subscription_id,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update payment method: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update payment method",
        )
