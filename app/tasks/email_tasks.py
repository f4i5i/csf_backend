"""Celery tasks for email automation."""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select

from app.models.child import Child
from app.models.class_ import Class
from app.models.enrollment import Enrollment
from app.models.order import OrderLineItem
from app.models.payment import InstallmentPayment, InstallmentPlan, Payment
from app.models.user import User
from app.services.email_service import email_service
from app.tasks.celery_app import celery_app
from core.db.session import async_session_factory

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="send_order_confirmation_email")
def send_order_confirmation_email(
    self,
    user_email: str,
    user_name: str,
    order_id: str,
    order_items: list[Dict[str, Any]],
    subtotal: str,
    discount_total: str,
    total: str,
    payment_type: str,
) -> bool:
    """Send order confirmation email.

    Args:
        user_email: Recipient email
        user_name: User's name
        order_id: Order ID
        order_items: List of order items
        subtotal: Subtotal amount (as string)
        discount_total: Discount amount (as string)
        total: Total amount (as string)
        payment_type: Payment type
    """
    try:
        success = email_service.send_order_confirmation(
            to_email=user_email,
            user_name=user_name,
            order_id=order_id,
            order_items=order_items,
            subtotal=Decimal(subtotal),
            discount_total=Decimal(discount_total),
            total=Decimal(total),
            payment_type=payment_type,
        )

        if success:
            logger.info(f"Order confirmation email sent to {user_email} for order {order_id}")
        else:
            logger.warning(f"Failed to send order confirmation email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending order confirmation email: {str(e)}")
        # Retry up to 3 times with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries), max_retries=3)


@celery_app.task(bind=True, name="send_enrollment_confirmation_email")
def send_enrollment_confirmation_email(
    self,
    user_email: str,
    user_name: str,
    child_name: str,
    class_name: str,
    start_date: str,
    end_date: str,
    class_location: str,
    class_time: str,
) -> bool:
    """Send enrollment confirmation email.

    Args:
        user_email: Recipient email
        user_name: Parent's name
        child_name: Child's name
        class_name: Class name
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        class_location: Location/venue
        class_time: Class time schedule
    """
    try:
        success = email_service.send_enrollment_confirmation(
            to_email=user_email,
            user_name=user_name,
            child_name=child_name,
            class_name=class_name,
            start_date=datetime.fromisoformat(start_date).date(),
            end_date=datetime.fromisoformat(end_date).date(),
            class_location=class_location,
            class_time=class_time,
        )

        if success:
            logger.info(f"Enrollment confirmation email sent to {user_email}")
        else:
            logger.warning(f"Failed to send enrollment confirmation email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending enrollment confirmation email: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries), max_retries=3)


@celery_app.task(bind=True, name="send_installment_reminder_email")
def send_installment_reminder_email(
    self,
    user_email: str,
    user_name: str,
    child_name: str,
    class_name: str,
    amount: str,
    due_date: str,
    installment_number: int,
    total_installments: int,
) -> bool:
    """Send installment payment reminder email.

    Args:
        user_email: Recipient email
        user_name: User's name
        child_name: Child's name
        class_name: Class name
        amount: Payment amount (as string)
        due_date: Due date (ISO format)
        installment_number: Current installment number
        total_installments: Total installments
    """
    try:
        success = email_service.send_installment_reminder(
            to_email=user_email,
            user_name=user_name,
            child_name=child_name,
            class_name=class_name,
            amount=Decimal(amount),
            due_date=datetime.fromisoformat(due_date).date(),
            installment_number=installment_number,
            total_installments=total_installments,
        )

        if success:
            logger.info(f"Installment reminder email sent to {user_email}")
        else:
            logger.warning(f"Failed to send installment reminder email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending installment reminder email: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries), max_retries=3)


@celery_app.task(bind=True, name="send_payment_success_email")
def send_payment_success_email(
    self,
    user_email: str,
    user_name: str,
    amount: str,
    payment_date: str,
    payment_method: str,
    transaction_id: str,
    receipt_url: Optional[str] = None,
) -> bool:
    """Send payment success confirmation email.

    Args:
        user_email: Recipient email
        user_name: User's name
        amount: Payment amount (as string)
        payment_date: Payment date (ISO format)
        payment_method: Payment method description
        transaction_id: Transaction ID
        receipt_url: Stripe receipt URL (optional)
    """
    try:
        success = email_service.send_payment_success(
            to_email=user_email,
            user_name=user_name,
            amount=Decimal(amount),
            payment_date=datetime.fromisoformat(payment_date),
            payment_method=payment_method,
            transaction_id=transaction_id,
            receipt_url=receipt_url,
        )

        if success:
            logger.info(f"Payment success email sent to {user_email}")
        else:
            logger.warning(f"Failed to send payment success email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending payment success email: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries), max_retries=3)


@celery_app.task(bind=True, name="send_payment_failed_email")
def send_payment_failed_email(
    self,
    user_email: str,
    user_name: str,
    amount: str,
    payment_date: str,
    payment_method: str,
    failure_reason: str,
    retry_instructions: str,
) -> bool:
    """Send payment failure notification email.

    Args:
        user_email: Recipient email
        user_name: User's name
        amount: Payment amount (as string)
        payment_date: Payment date (ISO format)
        payment_method: Payment method used
        failure_reason: Reason for failure
        retry_instructions: Instructions for retrying
    """
    try:
        success = email_service.send_payment_failed(
            to_email=user_email,
            user_name=user_name,
            amount=Decimal(amount),
            payment_date=datetime.fromisoformat(payment_date),
            payment_method=payment_method,
            failure_reason=failure_reason,
            retry_instructions=retry_instructions,
        )

        if success:
            logger.info(f"Payment failed email sent to {user_email}")
        else:
            logger.warning(f"Failed to send payment failed email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending payment failed email: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries), max_retries=3)


@celery_app.task(bind=True, name="send_cancellation_confirmation_email")
def send_cancellation_confirmation_email(
    self,
    user_email: str,
    user_name: str,
    child_name: str,
    class_name: str,
    cancellation_date: str,
    refund_amount: Optional[str] = None,
    effective_date: Optional[str] = None,
) -> bool:
    """Send cancellation confirmation email.

    Args:
        user_email: Recipient email
        user_name: Parent's name
        child_name: Child's name
        class_name: Class name
        cancellation_date: Cancellation date (ISO format)
        refund_amount: Refund amount (as string, optional)
        effective_date: Effective cancellation date (ISO format, optional)
    """
    try:
        success = email_service.send_cancellation_confirmation(
            to_email=user_email,
            user_name=user_name,
            child_name=child_name,
            class_name=class_name,
            cancellation_date=datetime.fromisoformat(cancellation_date).date(),
            refund_amount=Decimal(refund_amount) if refund_amount else None,
            effective_date=datetime.fromisoformat(effective_date).date() if effective_date else None,
        )

        if success:
            logger.info(f"Cancellation confirmation email sent to {user_email}")
        else:
            logger.warning(f"Failed to send cancellation confirmation email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending cancellation confirmation email: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries), max_retries=3)


@celery_app.task(name="send_upcoming_installment_reminders")
def send_upcoming_installment_reminders() -> Dict[str, Any]:
    """Periodic task to send reminders for upcoming installment payments.

    Runs daily via Celery Beat.
    Sends reminders for payments due within the next 3 days.
    """
    logger.info("Starting upcoming installment reminders task")

    try:
        # This needs to be run in async context
        import asyncio
        result = asyncio.run(_send_upcoming_installment_reminders_async())
        return result

    except Exception as e:
        logger.error(f"Error in send_upcoming_installment_reminders: {str(e)}")
        return {"success": False, "error": str(e)}


async def _send_upcoming_installment_reminders_async() -> Dict[str, Any]:
    """Async implementation of upcoming installment reminders."""
    async with async_session_factory() as db:
        # Find installment payments due in next 3 days
        today = date.today()
        reminder_date = today + timedelta(days=3)

        stmt = select(InstallmentPayment).where(
            InstallmentPayment.status == "pending",
            InstallmentPayment.due_date == reminder_date,
        )

        result = await db.execute(stmt)
        upcoming_payments = result.scalars().all()

        sent_count = 0
        failed_count = 0

        for payment in upcoming_payments:
            try:
                # Get related data
                plan = await db.get(InstallmentPlan, payment.installment_plan_id)
                user = await db.get(User, plan.user_id)

                # Get enrollment through order line items
                line_item_result = await db.execute(
                    select(OrderLineItem).where(OrderLineItem.order_id == plan.order_id).limit(1)
                )
                line_item = line_item_result.scalar_one_or_none()

                enrollment = None
                if line_item and line_item.enrollment_id:
                    enrollment = await db.get(Enrollment, line_item.enrollment_id)

                if enrollment:
                    class_ = await db.get(Class, enrollment.class_id)
                    child = await db.get(Child, enrollment.child_id)

                    # Send reminder email
                    send_installment_reminder_email.delay(
                        user_email=user.email,
                        user_name=user.full_name,
                        child_name=child.full_name,
                        class_name=class_.name,
                        amount=str(payment.amount),
                        due_date=payment.due_date.isoformat(),
                        installment_number=payment.installment_number,
                        total_installments=plan.num_installments,
                    )

                    sent_count += 1

            except Exception as e:
                logger.error(f"Error sending reminder for payment {payment.id}: {str(e)}")
                failed_count += 1

        logger.info(
            f"Upcoming installment reminders task completed: {sent_count} sent, {failed_count} failed"
        )

        return {"success": True, "sent": sent_count, "failed": failed_count}


# ============== Payment Retry Email Tasks ==============


@celery_app.task(name="send_payment_retry_success_email")
def send_payment_retry_success_email(
    user_email: str,
    user_name: str,
    amount: str,
    retry_attempt: int,
    transaction_id: str,
) -> bool:
    """Send email notification when payment retry succeeds."""
    try:
        subject = f"Payment Successful (Retry Attempt {retry_attempt})"

        body = f"""
        <h2>Payment Successful!</h2>
        <p>Hello {user_name},</p>

        <p>Great news! Your payment has been successfully processed on retry attempt {retry_attempt} of 3.</p>

        <p><strong>Payment Details:</strong></p>
        <ul>
            <li>Amount: ${amount}</li>
            <li>Transaction ID: {transaction_id}</li>
            <li>Retry Attempt: {retry_attempt} of 3</li>
        </ul>

        <p>Thank you for your patience. Your enrollment is now fully confirmed.</p>

        <p>Best regards,<br>The CSF Team</p>
        """

        return send_email(
            to_email=user_email,
            subject=subject,
            html_content=body,
        )

    except Exception as e:
        logger.error(f"Error sending payment retry success email: {str(e)}")
        return False


@celery_app.task(name="send_payment_retry_failed_email")
def send_payment_retry_failed_email(
    user_email: str,
    user_name: str,
    amount: str,
    retry_attempt: int,
    max_retries: int,
    failure_reason: str,
) -> bool:
    """Send email notification when payment retry fails."""
    try:
        retries_remaining = max_retries - retry_attempt

        if retries_remaining > 0:
            subject = f"Payment Retry Failed - {retries_remaining} Attempt(s) Remaining"
            next_steps = f"<p>We will automatically retry this payment. You have <strong>{retries_remaining} more attempt(s)</strong> remaining.</p>"
        else:
            subject = "Payment Failed - Maximum Retries Reached"
            next_steps = "<p><strong>Maximum retry attempts reached.</strong> Please update your payment method or contact support.</p>"

        body = f"""
        <h2>Payment Retry Failed</h2>
        <p>Hello {user_name},</p>

        <p>We attempted to process your payment but it was unsuccessful.</p>

        <p><strong>Payment Details:</strong></p>
        <ul>
            <li>Amount: ${amount}</li>
            <li>Retry Attempt: {retry_attempt} of {max_retries}</li>
            <li>Reason: {failure_reason}</li>
        </ul>

        {next_steps}

        <p><strong>What you can do:</strong></p>
        <ul>
            <li>Update your payment method in your account settings</li>
            <li>Contact your bank to ensure the card is active and has sufficient funds</li>
            <li>Contact us if you need assistance</li>
        </ul>

        <p>Best regards,<br>The CSF Team</p>
        """

        return send_email(
            to_email=user_email,
            subject=subject,
            html_content=body,
        )

    except Exception as e:
        logger.error(f"Error sending payment retry failed email: {str(e)}")
        return False


@celery_app.task(name="send_payment_max_retries_admin_notification")
def send_payment_max_retries_admin_notification(
    payment_id: str,
    user_email: str,
    user_name: str,
    amount: str,
    order_id: Optional[str] = None,
) -> bool:
    """Send admin notification when payment reaches max retry attempts."""
    try:
        # TODO: Get admin email from settings
        admin_email = "admin@csf.com"  # Replace with actual admin email

        subject = f"Action Required: Payment Failed After 3 Retry Attempts"

        body = f"""
        <h2>Payment Failed - Maximum Retries Reached</h2>
        <p>A payment has failed after 3 automatic retry attempts.</p>

        <p><strong>Payment Details:</strong></p>
        <ul>
            <li>Payment ID: {payment_id}</li>
            <li>Order ID: {order_id or 'N/A'}</li>
            <li>User: {user_name} ({user_email})</li>
            <li>Amount: ${amount}</li>
            <li>Retry Attempts: 3 of 3 (Maximum Reached)</li>
        </ul>

        <p><strong>Action Required:</strong></p>
        <ul>
            <li>Contact the user to resolve payment issue</li>
            <li>Review enrollment status and determine next steps</li>
            <li>Consider manual payment processing if needed</li>
        </ul>

        <p>View payment details in the admin portal.</p>

        <p>Best regards,<br>CSF System</p>
        """

        return send_email(
            to_email=admin_email,
            subject=subject,
            html_content=body,
        )

    except Exception as e:
        logger.error(f"Error sending admin max retries notification: {str(e)}")
        return False
