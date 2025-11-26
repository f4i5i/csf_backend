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
    """Periodic task to retry failed payments.

    Runs daily via Celery Beat.
    Retries payments that failed within the last 3 days.
    """
    logger.info("Starting retry failed payments task")

    try:
        import asyncio
        result = asyncio.run(_retry_failed_payments_async())
        return result

    except Exception as e:
        logger.error(f"Error in retry_failed_payments: {str(e)}")
        return {"success": False, "error": str(e)}


async def _retry_failed_payments_async() -> Dict[str, Any]:
    """Async implementation of retry failed payments."""
    async with async_session_factory() as db:
        # Find failed payments from last 3 days
        cutoff_date = date.today() - timedelta(days=3)

        stmt = (
            select(InstallmentPayment)
            .join(InstallmentPlan)
            .where(
                InstallmentPayment.status == "failed",
                InstallmentPayment.due_date >= cutoff_date,
            )
        )

        result = await db.execute(stmt)
        failed_payments = result.scalars().all()

        retried_count = 0
        success_count = 0
        failed_count = 0

        stripe_service = StripeService()

        for payment in failed_payments:
            try:
                plan = await db.get(InstallmentPlan, payment.installment_plan_id)
                user = await db.get(User, plan.user_id)

                if not plan.stripe_subscription_id:
                    logger.warning(f"No Stripe subscription for plan {plan.id}")
                    continue

                # Get latest invoice from subscription
                subscription = stripe.Subscription.retrieve(
                    plan.stripe_subscription_id
                )

                if subscription.latest_invoice:
                    invoice = stripe.Invoice.retrieve(subscription.latest_invoice)

                    # Retry payment if invoice is still open
                    if invoice.status == "open":
                        try:
                            # Attempt to pay invoice
                            paid_invoice = stripe.Invoice.pay(invoice.id)

                            if paid_invoice.status == "paid":
                                # Update payment status
                                payment.status = "paid"
                                payment.stripe_payment_intent_id = paid_invoice.payment_intent
                                await db.commit()

                                # Send success email
                                send_payment_success_email.delay(
                                    user_email=user.email,
                                    user_name=user.full_name,
                                    amount=str(payment.amount),
                                    payment_date=date.today().isoformat(),
                                    payment_method="Saved payment method",
                                    transaction_id=paid_invoice.payment_intent,
                                    receipt_url=paid_invoice.hosted_invoice_url,
                                )

                                success_count += 1
                                logger.info(f"Successfully retried payment {payment.id}")

                        except Exception as pay_error:
                            logger.error(f"Failed to retry payment {payment.id}: {str(pay_error)}")
                            failed_count += 1

                retried_count += 1

            except Exception as e:
                logger.error(f"Error processing payment {payment.id}: {str(e)}")
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
