"""Celery tasks for payment processing and retries."""

import logging
from datetime import date, timedelta
from typing import Any, Dict

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import InstallmentPayment, InstallmentPlan, Payment
from app.models.user import User
from app.services.stripe_service import StripeService
from app.tasks.celery_app import celery_app
from app.tasks.email_tasks import send_payment_failed_email, send_payment_success_email
from core.db.session import async_session_factory

logger = logging.getLogger(__name__)


@celery_app.task(name="retry_failed_payments")
def retry_failed_payments() -> Dict[str, Any]:
    """Periodic task to retry failed payments with 3-attempt system.

    Runs every 30 minutes via Celery Beat.
    Retries payments that are due for retry based on next_retry_at field.
    Uses exponential backoff: 1 hour, 4 hours, 12 hours.
    """
    logger.info("Starting retry failed payments task (3-attempt system)")

    try:
        import asyncio
        result = asyncio.run(_retry_failed_payments_async())
        return result

    except Exception as e:
        logger.error(f"Error in retry_failed_payments: {str(e)}")
        return {"success": False, "error": str(e)}


async def _retry_failed_payments_async() -> Dict[str, Any]:
    """Async implementation of retry failed payments."""
    from app.models.payment import PaymentStatus
    from app.tasks.email_tasks import send_email

    async with async_session_factory() as db:
        # Get payments that are due for retry
        payments_to_retry = await Payment.get_payments_due_for_retry(db)

        if not payments_to_retry:
            logger.info("No payments due for retry")
            return {"success": True, "attempted": 0, "succeeded": 0, "failed": 0}

        logger.info(f"Found {len(payments_to_retry)} payments due for retry")

        retried_count = 0
        success_count = 0
        failed_count = 0

        stripe_service = StripeService()

        for payment in payments_to_retry:
            try:
                # Record retry attempt
                await payment.record_retry_attempt(db)

                user = payment.user
                order = payment.order

                logger.info(
                    f"Retrying payment {payment.id} (attempt {payment.retry_count}/3)"
                )

                # Attempt to retry the payment intent
                if payment.stripe_payment_intent_id:
                    try:
                        # Confirm the payment intent again
                        payment_intent = stripe.PaymentIntent.retrieve(
                            payment.stripe_payment_intent_id
                        )

                        # If payment intent requires action, we can't auto-retry
                        if payment_intent.status == "requires_payment_method":
                            # Try to charge with customer's default payment method
                            customer = stripe.Customer.retrieve(user.stripe_customer_id)

                            if customer.invoice_settings.default_payment_method:
                                payment_intent = stripe.PaymentIntent.modify(
                                    payment.stripe_payment_intent_id,
                                    payment_method=customer.invoice_settings.default_payment_method,
                                )
                                payment_intent = stripe.PaymentIntent.confirm(
                                    payment.stripe_payment_intent_id
                                )

                        if payment_intent.status == "succeeded":
                            # Payment succeeded!
                            await payment.mark_succeeded(db)
                            success_count += 1

                            # Send success email
                            send_payment_retry_success_email.delay(
                                user_email=user.email,
                                user_name=user.full_name,
                                amount=str(payment.amount),
                                retry_attempt=payment.retry_count,
                                transaction_id=payment.stripe_payment_intent_id,
                            )

                            logger.info(f"Payment {payment.id} succeeded on retry")

                        else:
                            # Payment still failed
                            failed_count += 1

                            # Send retry failure email
                            send_payment_retry_failed_email.delay(
                                user_email=user.email,
                                user_name=user.full_name,
                                amount=str(payment.amount),
                                retry_attempt=payment.retry_count,
                                max_retries=3,
                                failure_reason=payment.failure_reason or "Payment method declined",
                            )

                            # Schedule next retry if not at max attempts
                            if payment.retry_count < 3:
                                await payment.schedule_retry(db)
                                logger.info(
                                    f"Payment {payment.id} failed, scheduled for retry at {payment.next_retry_at}"
                                )
                            else:
                                # Max retries reached, notify admin
                                send_payment_max_retries_admin_notification.delay(
                                    payment_id=payment.id,
                                    user_email=user.email,
                                    user_name=user.full_name,
                                    amount=str(payment.amount),
                                    order_id=order.id if order else None,
                                )
                                logger.warning(
                                    f"Payment {payment.id} reached max retries, admin notified"
                                )

                    except stripe.error.StripeError as stripe_error:
                        logger.error(
                            f"Stripe error retrying payment {payment.id}: {str(stripe_error)}"
                        )
                        failed_count += 1

                        # Send retry failure email
                        send_payment_retry_failed_email.delay(
                            user_email=user.email,
                            user_name=user.full_name,
                            amount=str(payment.amount),
                            retry_attempt=payment.retry_count,
                            max_retries=3,
                            failure_reason=str(stripe_error),
                        )

                        # Schedule next retry if not at max attempts
                        if payment.retry_count < 3:
                            await payment.schedule_retry(db)
                        else:
                            # Max retries reached, notify admin
                            send_payment_max_retries_admin_notification.delay(
                                payment_id=payment.id,
                                user_email=user.email,
                                user_name=user.full_name,
                                amount=str(payment.amount),
                                order_id=order.id if order else None,
                            )

                retried_count += 1

            except Exception as e:
                logger.error(f"Error retrying payment {payment.id}: {str(e)}", exc_info=True)
                failed_count += 1

        logger.info(
            f"Retry failed payments task completed: {retried_count} attempted, "
            f"{success_count} succeeded, {failed_count} failed"
        )

        return {
            "success": True,
            "attempted": retried_count,
            "succeeded": success_count,
            "failed": failed_count,
        }


@celery_app.task(bind=True, name="process_overdue_installments")
def process_overdue_installments(self) -> Dict[str, Any]:
    """Process overdue installment payments.

    Marks installments as overdue if past due date.
    Sends notifications to users.
    """
    logger.info("Starting process overdue installments task")

    try:
        import asyncio
        result = asyncio.run(_process_overdue_installments_async())
        return result

    except Exception as e:
        logger.error(f"Error in process_overdue_installments: {str(e)}")
        return {"success": False, "error": str(e)}


async def _process_overdue_installments_async() -> Dict[str, Any]:
    """Async implementation of process overdue installments."""
    async with async_session_factory() as db:
        # Find payments that are past due
        today = date.today()

        stmt = select(InstallmentPayment).where(
            InstallmentPayment.status == "pending",
            InstallmentPayment.due_date < today,
        )

        result = await db.execute(stmt)
        overdue_payments = result.scalars().all()

        processed_count = 0

        for payment in overdue_payments:
            try:
                # Update status to failed (overdue payments are considered failed)
                payment.status = "failed"
                await db.commit()

                # Get user and send notification
                plan = await db.get(InstallmentPlan, payment.installment_plan_id)
                user = await db.get(User, plan.user_id)

                # Send overdue notification (using payment failed template)
                send_payment_failed_email.delay(
                    user_email=user.email,
                    user_name=user.full_name,
                    amount=str(payment.amount),
                    payment_date=payment.due_date.isoformat(),
                    payment_method="Saved payment method",
                    failure_reason="Payment is now overdue",
                    retry_instructions="Please update your payment method and retry immediately to avoid enrollment cancellation.",
                )

                processed_count += 1
                logger.info(f"Marked payment {payment.id} as overdue")

            except Exception as e:
                logger.error(f"Error processing overdue payment {payment.id}: {str(e)}")

        logger.info(f"Process overdue installments completed: {processed_count} processed")

        return {"success": True, "processed": processed_count}
