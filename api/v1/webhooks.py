"""Stripe webhook handler for processing payment events."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child
from app.models.class_ import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.order import Order, OrderLineItem, OrderStatus
from app.models.program import Program, School
from app.models.payment import (
    InstallmentPayment,
    InstallmentPaymentStatus,
    InstallmentPlan,
    InstallmentPlanStatus,
    Payment,
    PaymentStatus,
    PaymentType,
)
from app.models.user import User
from app.services.stripe_service import StripeService
from app.tasks.email_tasks import (
    send_enrollment_confirmation_email,
    send_payment_failed_email,
    send_payment_success_email,
)
from core.db import get_db
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db_session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Handle Stripe webhook events.

    Processes payment success/failure and updates order/enrollment status.
    """
    payload = await request.body()

    try:
        event = StripeService.construct_event(payload, stripe_signature)
    except ValueError:
        logger.error("Invalid webhook payload")
        return {"error": "Invalid payload"}, 400
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return {"error": "Invalid signature"}, 400

    event_type = event["type"]
    logger.info(f"Received Stripe webhook: {event_type}")

    # Handle different event types
    if event_type == "checkout.session.completed":
        await handle_checkout_session_completed(event["data"]["object"], db_session)

    elif event_type == "payment_intent.succeeded":
        await handle_payment_succeeded(event["data"]["object"], db_session)

    elif event_type == "payment_intent.payment_failed":
        await handle_payment_failed(event["data"]["object"], db_session)

    elif event_type == "invoice.paid":
        await handle_invoice_paid(event["data"]["object"], db_session)

    elif event_type == "invoice.payment_failed":
        await handle_invoice_failed(event["data"]["object"], db_session)

    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(event["data"]["object"], db_session)

    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(event["data"]["object"], db_session)

    elif event_type == "charge.refunded":
        await handle_charge_refunded(event["data"]["object"], db_session)

    elif event_type == "invoice.upcoming":
        await handle_invoice_upcoming(event["data"]["object"], db_session)

    return {"status": "success"}


async def handle_checkout_session_completed(
    session: dict,
    db_session: AsyncSession,
) -> None:
    """
    Handle completed Stripe Checkout Session.

    Extracts payment intent from session and delegates to payment handler.
    """
    session_id = session["id"]
    payment_intent_id = session.get("payment_intent")

    logger.info(f"Processing checkout session completed: {session_id}, payment_intent: {payment_intent_id}")

    if not payment_intent_id:
        logger.warning(f"No payment intent in checkout session: {session_id}")
        return

    # Retrieve the full payment intent object
    import stripe
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        # Delegate to existing payment succeeded handler
        await handle_payment_succeeded(payment_intent, db_session)
    except Exception as e:
        logger.error(f"Failed to retrieve payment intent {payment_intent_id}: {e}")
        raise


async def handle_payment_succeeded(
    payment_intent: dict,
    db_session: AsyncSession,
) -> None:
    """Handle successful one-time payment."""
    payment_intent_id = payment_intent["id"]
    logger.info(f"Processing payment success: {payment_intent_id}")

    # Find order by payment intent
    result = await db_session.execute(
        select(Order).where(Order.stripe_payment_intent_id == payment_intent_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        logger.warning(f"No order found for payment intent: {payment_intent_id}")
        return

    # Update order status
    order.status = OrderStatus.PAID
    order.paid_at = datetime.now(timezone.utc)

    # Create payment record
    amount = StripeService.cents_to_dollars(payment_intent["amount"])
    payment = Payment(
        id=str(uuid4()),
        order_id=order.id,
        user_id=order.user_id,
        payment_type=PaymentType.ONE_TIME,
        status=PaymentStatus.SUCCEEDED,
        amount=amount,
        currency=payment_intent["currency"].upper(),
        stripe_payment_intent_id=payment_intent_id,
        stripe_charge_id=payment_intent.get("latest_charge"),
        refund_amount=0,
        paid_at=datetime.now(timezone.utc),
        organization_id=order.organization_id,
    )
    db_session.add(payment)

    # Activate enrollments - ONLY those in this specific order
    # Get enrollment IDs from order line items
    line_items_result = await db_session.execute(
        select(OrderLineItem).where(OrderLineItem.order_id == order.id)
    )
    line_items = line_items_result.scalars().all()
    enrollment_ids = [li.enrollment_id for li in line_items if li.enrollment_id]

    # Get enrollments for this order only
    enrollment_result = await db_session.execute(
        select(Enrollment).where(
            Enrollment.id.in_(enrollment_ids),
            Enrollment.status == EnrollmentStatus.PENDING,
        )
    )
    enrollments = enrollment_result.scalars().all()

    # Get user for email
    user_result = await db_session.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalar_one_or_none()

    for enrollment in enrollments:
        enrollment.status = EnrollmentStatus.ACTIVE
        enrollment.enrolled_at = datetime.now(timezone.utc)

        # Update class enrollment count
        class_result = await db_session.execute(
            select(Class).where(Class.id == enrollment.class_id)
        )
        class_ = class_result.scalar_one_or_none()
        if class_:
            class_.current_enrollment += 1

            # Send enrollment confirmation email
            if user:
                child_result = await db_session.execute(
                    select(Child).where(Child.id == enrollment.child_id)
                )
                child = child_result.scalar_one_or_none()

                if child:
                    # Get school for location
                    school_result = await db_session.execute(
                        select(School).where(School.id == class_.school_id)
                    )
                    school = school_result.scalar_one_or_none()
                    class_location = school.name if school else "TBD"

                    send_enrollment_confirmation_email.delay(
                        user_email=user.email,
                        user_name=user.full_name,
                        child_name=child.full_name,
                        class_name=class_.name,
                        start_date=class_.start_date.isoformat(),
                        end_date=class_.end_date.isoformat(),
                        class_location=class_location,
                        class_time=f"{class_.start_time} - {class_.end_time}" if class_.start_time else "TBD",
                    )


    await db_session.commit()
    logger.info(f"Order {order.id} marked as paid, {len(enrollments)} enrollments activated")

    # Send payment success email
    if user and payment_intent.get("latest_charge"):
        send_payment_success_email.delay(
            user_email=user.email,
            user_name=user.full_name,
            amount=str(amount),
            payment_date=datetime.now(timezone.utc).isoformat(),
            payment_method="Credit Card",
            transaction_id=payment_intent_id,
            receipt_url=payment_intent.get("receipt_url"),
        )



async def handle_payment_failed(
    payment_intent: dict,
    db_session: AsyncSession,
) -> None:
    """Handle failed payment."""
    payment_intent_id = payment_intent["id"]
    logger.info(f"Processing payment failure: {payment_intent_id}")

    # Find order by payment intent
    result = await db_session.execute(
        select(Order).where(Order.stripe_payment_intent_id == payment_intent_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        logger.warning(f"No order found for payment intent: {payment_intent_id}")
        return

    # Create failed payment record
    amount = StripeService.cents_to_dollars(payment_intent["amount"])
    failure_message = None
    if payment_intent.get("last_payment_error"):
        failure_message = payment_intent["last_payment_error"].get("message")

    payment = Payment(
        id=str(uuid4()),
        order_id=order.id,
        user_id=order.user_id,
        payment_type=PaymentType.ONE_TIME,
        status=PaymentStatus.FAILED,
        amount=amount,
        currency=payment_intent["currency"].upper(),
        stripe_payment_intent_id=payment_intent_id,
        failure_reason=failure_message,
        refund_amount=0,
        organization_id=order.organization_id,
    )
    db_session.add(payment)

    await db_session.commit()
    logger.info(f"Payment failure recorded for order {order.id}")

    # Send payment failed email
    user_result = await db_session.execute(select(User).where(User.id == order.user_id))
    user = user_result.scalar_one_or_none()

    if user:
        send_payment_failed_email.delay(
            user_email=user.email,
            user_name=user.full_name,
            amount=str(amount),
            payment_date=datetime.now(timezone.utc).isoformat(),
            payment_method="Credit Card",
            failure_reason=failure_message or "Payment declined",
            retry_instructions="Please update your payment method or try a different card.",
        )


async def handle_invoice_paid(
    invoice: dict,
    db_session: AsyncSession,
) -> None:
    """Handle paid invoice (for subscriptions/installments)."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    logger.info(f"Processing invoice paid for subscription: {subscription_id}")

    # Find installment plan
    result = await db_session.execute(
        select(InstallmentPlan).where(
            InstallmentPlan.stripe_subscription_id == subscription_id
        )
    )
    plan = result.scalar_one_or_none()

    if not plan:
        logger.warning(f"No installment plan found for subscription: {subscription_id}")
        return

    # Find the next pending installment
    installment_result = await db_session.execute(
        select(InstallmentPayment)
        .where(
            InstallmentPayment.installment_plan_id == plan.id,
            InstallmentPayment.status == InstallmentPaymentStatus.PENDING,
        )
        .order_by(InstallmentPayment.installment_number)
        .limit(1)
    )
    installment = installment_result.scalar_one_or_none()

    if installment:
        # Create payment record
        amount = StripeService.cents_to_dollars(invoice["amount_paid"])
        payment = Payment(
            id=str(uuid4()),
            order_id=plan.order_id,
            user_id=plan.user_id,
            payment_type=PaymentType.INSTALLMENT,
            status=PaymentStatus.SUCCEEDED,
            amount=amount,
            currency=invoice["currency"].upper(),
            stripe_subscription_id=subscription_id,
            refund_amount=0,
            paid_at=datetime.now(timezone.utc),
            organization_id=plan.organization_id,
        )
        db_session.add(payment)

        # Update installment
        installment.status = InstallmentPaymentStatus.PAID
        installment.payment_id = payment.id
        installment.paid_at = datetime.now(timezone.utc)

        # Check if all installments are paid
        remaining_result = await db_session.execute(
            select(InstallmentPayment).where(
                InstallmentPayment.installment_plan_id == plan.id,
                InstallmentPayment.status == InstallmentPaymentStatus.PENDING,
            )
        )
        remaining = remaining_result.scalars().all()

        if len(remaining) == 0:
            plan.status = InstallmentPlanStatus.COMPLETED
            logger.info(f"Installment plan {plan.id} completed")

        await db_session.commit()
        logger.info(f"Installment {installment.installment_number} of {plan.num_installments} paid")

        # Send payment success email
        user_result = await db_session.execute(select(User).where(User.id == plan.user_id))
        user = user_result.scalar_one_or_none()

        if user:
            send_payment_success_email.delay(
                user_email=user.email,
                user_name=user.full_name,
                amount=str(amount),
                payment_date=datetime.now(timezone.utc).isoformat(),
                payment_method="Saved payment method",
                transaction_id=payment.id,
                receipt_url=invoice.get("hosted_invoice_url"),
            )



async def handle_invoice_failed(
    invoice: dict,
    db_session: AsyncSession,
) -> None:
    """Handle failed invoice payment."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    logger.info(f"Processing invoice failure for subscription: {subscription_id}")

    # Find installment plan
    result = await db_session.execute(
        select(InstallmentPlan).where(
            InstallmentPlan.stripe_subscription_id == subscription_id
        )
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return

    # Find the pending installment
    installment_result = await db_session.execute(
        select(InstallmentPayment)
        .where(
            InstallmentPayment.installment_plan_id == plan.id,
            InstallmentPayment.status == InstallmentPaymentStatus.PENDING,
        )
        .order_by(InstallmentPayment.installment_number)
        .limit(1)
    )
    installment = installment_result.scalar_one_or_none()

    if installment:
        installment.attempt_count += 1

        # If too many failures, mark as failed
        if installment.attempt_count >= 3:
            installment.status = InstallmentPaymentStatus.FAILED
            plan.status = InstallmentPlanStatus.DEFAULTED
            logger.warning(f"Installment plan {plan.id} defaulted after 3 failed attempts")

        await db_session.commit()

        # Send payment failed email
        user_result = await db_session.execute(select(User).where(User.id == plan.user_id))
        user = user_result.scalar_one_or_none()

        if user:
            amount = StripeService.cents_to_dollars(invoice.get("amount_due", 0))
            failure_reason = "Payment declined"
            if invoice.get("last_finalization_error"):
                failure_reason = invoice["last_finalization_error"].get("message", failure_reason)

            send_payment_failed_email.delay(
                user_email=user.email,
                user_name=user.full_name,
                amount=str(amount),
                payment_date=datetime.now(timezone.utc).isoformat(),
                payment_method="Saved payment method",
                failure_reason=failure_reason,
                retry_instructions="Please update your payment method immediately to avoid enrollment cancellation.",
            )


async def handle_subscription_deleted(
    subscription: dict,
    db_session: AsyncSession,
) -> None:
    """Handle subscription cancellation."""
    subscription_id = subscription["id"]
    logger.info(f"Processing subscription deletion: {subscription_id}")

    # Find installment plan
    result = await db_session.execute(
        select(InstallmentPlan).where(
            InstallmentPlan.stripe_subscription_id == subscription_id
        )
    )
    plan = result.scalar_one_or_none()

    if plan and plan.status == InstallmentPlanStatus.ACTIVE:
        plan.status = InstallmentPlanStatus.CANCELLED
        await db_session.commit()
        logger.info(f"Installment plan {plan.id} cancelled")


async def handle_subscription_updated(
    subscription: dict,
    db_session: AsyncSession,
) -> None:
    """Handle subscription updates (status changes, payment method updates, etc)."""
    subscription_id = subscription["id"]
    logger.info(f"Processing subscription update: {subscription_id}")

    # Find installment plan or membership subscription
    result = await db_session.execute(
        select(InstallmentPlan).where(
            InstallmentPlan.stripe_subscription_id == subscription_id
        )
    )
    plan = result.scalar_one_or_none()

    if not plan:
        logger.warning(f"No plan found for subscription: {subscription_id}")
        return

    # Handle subscription status changes
    subscription_status = subscription.get("status")

    if subscription_status == "canceled" and plan.status == InstallmentPlanStatus.ACTIVE:
        plan.status = InstallmentPlanStatus.CANCELLED
        logger.info(f"Installment plan {plan.id} cancelled via subscription update")

    elif subscription_status == "past_due":
        logger.warning(f"Subscription {subscription_id} is past due")
        # TODO: Send notification to user

    elif subscription_status == "unpaid":
        logger.warning(f"Subscription {subscription_id} is unpaid")
        # Mark plan as defaulted if unpaid for too long
        if plan.status == InstallmentPlanStatus.ACTIVE:
            plan.status = InstallmentPlanStatus.DEFAULTED
            logger.warning(f"Installment plan {plan.id} defaulted due to non-payment")

    await db_session.commit()


async def handle_charge_refunded(
    charge: dict,
    db_session: AsyncSession,
) -> None:
    """Handle refunded charges."""
    charge_id = charge["id"]
    refund_amount_cents = charge.get("amount_refunded", 0)
    refund_amount = StripeService.cents_to_dollars(refund_amount_cents)

    logger.info(f"Processing refund for charge: {charge_id}, amount: ${refund_amount}")

    # Find payment by charge ID
    result = await db_session.execute(
        select(Payment).where(Payment.stripe_charge_id == charge_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        logger.warning(f"No payment found for charge: {charge_id}")
        return

    # Update payment refund amount
    payment.refund_amount = refund_amount
    payment.status = PaymentStatus.REFUNDED if refund_amount >= payment.amount else PaymentStatus.PARTIALLY_REFUNDED

    # Update order status if fully refunded
    if refund_amount >= payment.amount:
        order_result = await db_session.execute(
            select(Order).where(Order.id == payment.order_id)
        )
        order = order_result.scalar_one_or_none()

        if order:
            order.status = OrderStatus.REFUNDED
            logger.info(f"Order {order.id} marked as refunded")

            # Cancel associated enrollments - ONLY those in this specific order
            # Get enrollment IDs from order line items
            line_items_result = await db_session.execute(
                select(OrderLineItem).where(OrderLineItem.order_id == order.id)
            )
            line_items = line_items_result.scalars().all()
            enrollment_ids = [li.enrollment_id for li in line_items if li.enrollment_id]

            # Get enrollments for this order only
            enrollment_result = await db_session.execute(
                select(Enrollment).where(
                    Enrollment.id.in_(enrollment_ids),
                    Enrollment.status == EnrollmentStatus.ACTIVE,
                )
            )
            enrollments = enrollment_result.scalars().all()

            for enrollment in enrollments:
                enrollment.status = EnrollmentStatus.CANCELLED
                enrollment.cancelled_at = datetime.now(timezone.utc)

                # Update class enrollment count
                class_result = await db_session.execute(
                    select(Class).where(Class.id == enrollment.class_id)
                )
                class_ = class_result.scalar_one_or_none()
                if class_ and class_.current_enrollment > 0:
                    class_.current_enrollment -= 1

            logger.info(f"Cancelled {len(enrollments)} enrollments for refunded order")

    await db_session.commit()
    logger.info(f"Refund of ${refund_amount} processed for payment {payment.id}")


async def handle_invoice_upcoming(
    invoice: dict,
    db_session: AsyncSession,
) -> None:
    """Handle upcoming invoice (send payment reminders)."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    amount_due = StripeService.cents_to_dollars(invoice.get("amount_due", 0))
    next_payment_date = datetime.fromtimestamp(
        invoice.get("period_end", 0), tz=timezone.utc
    )

    logger.info(
        f"Upcoming invoice for subscription {subscription_id}: "
        f"${amount_due} due on {next_payment_date.date()}"
    )

    # Find installment plan
    result = await db_session.execute(
        select(InstallmentPlan).where(
            InstallmentPlan.stripe_subscription_id == subscription_id
        )
    )
    plan = result.scalar_one_or_none()

    if not plan:
        return

    # Find the next pending installment
    installment_result = await db_session.execute(
        select(InstallmentPayment)
        .where(
            InstallmentPayment.installment_plan_id == plan.id,
            InstallmentPayment.status == InstallmentPaymentStatus.PENDING,
        )
        .order_by(InstallmentPayment.installment_number)
        .limit(1)
    )
    installment = installment_result.scalar_one_or_none()

    if installment:
        logger.info(
            f"Payment reminder: Installment {installment.installment_number} of "
            f"{plan.num_installments} for user {plan.user_id} - ${amount_due}"
        )

        # TODO: Send email reminder to user
        # from app.tasks.email_tasks import send_installment_reminder
        # send_installment_reminder.delay(
        #     user_id=plan.user_id,
        #     amount=str(amount_due),
        #     due_date=str(next_payment_date.date()),
        #     installment_number=installment.installment_number,
        #     total_installments=plan.num_installments,
        # )

    # Note: Email sending would be implemented in Milestone 4
    # For now, just log the reminder
