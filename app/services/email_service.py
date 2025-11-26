"""Email service for sending transactional emails."""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from core.config import config

logger = logging.getLogger(__name__)

# Initialize Jinja2 template environment
template_env = Environment(
    loader=FileSystemLoader("app/templates/email"),
    autoescape=select_autoescape(["html", "xml"]),
)


class EmailService:
    """Service for sending transactional emails using SendGrid."""

    def __init__(self):
        """Initialize email service."""
        self.client = SendGridAPIClient(config.SENDGRID_API_KEY) if config.SENDGRID_API_KEY else None
        self.from_email = config.SENDGRID_FROM_EMAIL

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context."""
        template = template_env.get_template(template_name)
        return template.render(**context)

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        cc_emails: Optional[list[str]] = None,
        bcc_emails: Optional[list[str]] = None,
    ) -> bool:
        """Send email using SendGrid."""
        if not self.client:
            logger.warning(
                f"SendGrid not configured. Would send email to {to_email} with subject: {subject}"
            )
            return False

        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content,
            )

            if cc_emails:
                message.cc = cc_emails
            if bcc_emails:
                message.bcc = bcc_emails

            response = self.client.send(message)
            logger.info(f"Email sent to {to_email}: {subject} (Status: {response.status_code})")
            return response.status_code in [200, 201, 202]

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def send_order_confirmation(
        self,
        to_email: str,
        user_name: str,
        order_id: str,
        order_items: list[Dict[str, Any]],
        subtotal: Decimal,
        discount_total: Decimal,
        total: Decimal,
        payment_type: str,
    ) -> bool:
        """Send order confirmation email.

        Args:
            to_email: Recipient email address
            user_name: User's full name
            order_id: Order ID
            order_items: List of order items with details
            subtotal: Order subtotal
            discount_total: Total discounts applied
            total: Order total
            payment_type: Payment type (one-time, subscription, installment)
        """
        context = {
            "user_name": user_name,
            "order_id": order_id,
            "order_items": order_items,
            "subtotal": f"${subtotal:.2f}",
            "discount_total": f"${discount_total:.2f}",
            "total": f"${total:.2f}",
            "payment_type": payment_type,
            "frontend_url": config.FRONTEND_URL,
        }

        html_content = self._render_template("order_confirmation.html", context)
        return self._send_email(
            to_email=to_email,
            subject=f"Order Confirmation - {order_id}",
            html_content=html_content,
        )

    def send_enrollment_confirmation(
        self,
        to_email: str,
        user_name: str,
        child_name: str,
        class_name: str,
        start_date: date,
        end_date: date,
        class_location: str,
        class_time: str,
    ) -> bool:
        """Send enrollment confirmation email.

        Args:
            to_email: Recipient email address
            user_name: Parent's name
            child_name: Child's name
            class_name: Class name
            start_date: Class start date
            end_date: Class end date
            class_location: Location/venue
            class_time: Class time schedule
        """
        context = {
            "user_name": user_name,
            "child_name": child_name,
            "class_name": class_name,
            "start_date": start_date.strftime("%B %d, %Y"),
            "end_date": end_date.strftime("%B %d, %Y"),
            "class_location": class_location,
            "class_time": class_time,
            "frontend_url": config.FRONTEND_URL,
        }

        html_content = self._render_template("enrollment_confirmation.html", context)
        return self._send_email(
            to_email=to_email,
            subject=f"Enrollment Confirmed: {child_name} - {class_name}",
            html_content=html_content,
        )

    def send_installment_reminder(
        self,
        to_email: str,
        user_name: str,
        child_name: str,
        class_name: str,
        amount: Decimal,
        due_date: date,
        installment_number: int,
        total_installments: int,
    ) -> bool:
        """Send upcoming installment payment reminder.

        Args:
            to_email: Recipient email address
            user_name: User's name
            child_name: Child's name
            class_name: Class name
            amount: Payment amount
            due_date: Payment due date
            installment_number: Current installment number
            total_installments: Total number of installments
        """
        context = {
            "user_name": user_name,
            "child_name": child_name,
            "class_name": class_name,
            "amount": f"${amount:.2f}",
            "due_date": due_date.strftime("%B %d, %Y"),
            "installment_number": installment_number,
            "total_installments": total_installments,
            "frontend_url": config.FRONTEND_URL,
        }

        html_content = self._render_template("installment_reminder.html", context)
        return self._send_email(
            to_email=to_email,
            subject=f"Payment Reminder: Installment {installment_number}/{total_installments} Due Soon",
            html_content=html_content,
        )

    def send_payment_success(
        self,
        to_email: str,
        user_name: str,
        amount: Decimal,
        payment_date: datetime,
        payment_method: str,
        transaction_id: str,
        receipt_url: Optional[str] = None,
    ) -> bool:
        """Send payment success confirmation.

        Args:
            to_email: Recipient email address
            user_name: User's name
            amount: Payment amount
            payment_date: Payment date
            payment_method: Payment method (e.g., "Visa ending in 4242")
            transaction_id: Transaction ID
            receipt_url: Stripe receipt URL (optional)
        """
        context = {
            "user_name": user_name,
            "amount": f"${amount:.2f}",
            "payment_date": payment_date.strftime("%B %d, %Y at %I:%M %p"),
            "payment_method": payment_method,
            "transaction_id": transaction_id,
            "receipt_url": receipt_url,
            "frontend_url": config.FRONTEND_URL,
        }

        html_content = self._render_template("payment_success.html", context)
        return self._send_email(
            to_email=to_email,
            subject=f"Payment Received - ${amount:.2f}",
            html_content=html_content,
        )

    def send_payment_failed(
        self,
        to_email: str,
        user_name: str,
        amount: Decimal,
        payment_date: datetime,
        payment_method: str,
        failure_reason: str,
        retry_instructions: str,
    ) -> bool:
        """Send payment failure notification.

        Args:
            to_email: Recipient email address
            user_name: User's name
            amount: Payment amount
            payment_date: Attempted payment date
            payment_method: Payment method used
            failure_reason: Reason for failure
            retry_instructions: Instructions for retrying payment
        """
        context = {
            "user_name": user_name,
            "amount": f"${amount:.2f}",
            "payment_date": payment_date.strftime("%B %d, %Y at %I:%M %p"),
            "payment_method": payment_method,
            "failure_reason": failure_reason,
            "retry_instructions": retry_instructions,
            "frontend_url": config.FRONTEND_URL,
        }

        html_content = self._render_template("payment_failed.html", context)
        return self._send_email(
            to_email=to_email,
            subject=f"Payment Failed - Action Required",
            html_content=html_content,
        )

    def send_cancellation_confirmation(
        self,
        to_email: str,
        user_name: str,
        child_name: str,
        class_name: str,
        cancellation_date: date,
        refund_amount: Optional[Decimal] = None,
        effective_date: Optional[date] = None,
    ) -> bool:
        """Send enrollment cancellation confirmation.

        Args:
            to_email: Recipient email address
            user_name: Parent's name
            child_name: Child's name
            class_name: Class name
            cancellation_date: Date cancellation was requested
            refund_amount: Refund amount (if applicable)
            effective_date: Effective cancellation date (if different from request date)
        """
        context = {
            "user_name": user_name,
            "child_name": child_name,
            "class_name": class_name,
            "cancellation_date": cancellation_date.strftime("%B %d, %Y"),
            "refund_amount": f"${refund_amount:.2f}" if refund_amount else None,
            "effective_date": effective_date.strftime("%B %d, %Y") if effective_date else None,
            "frontend_url": config.FRONTEND_URL,
        }

        html_content = self._render_template("cancellation_confirmation.html", context)
        return self._send_email(
            to_email=to_email,
            subject=f"Cancellation Confirmed: {child_name} - {class_name}",
            html_content=html_content,
        )


# Singleton instance
email_service = EmailService()
