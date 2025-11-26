"""Stripe payment service for handling payments."""

import stripe
from decimal import Decimal
from typing import Optional

from core.config import config as settings
from core.logging import get_logger

logger = get_logger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service for interacting with Stripe API."""

    # ============== Customer Management ==============

    @staticmethod
    async def create_customer(
        email: str, name: str = None, metadata: dict = None
    ) -> str:
        """Create a new Stripe customer."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            logger.info(f"Created Stripe customer: {customer.id}")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise

    @staticmethod
    async def get_or_create_customer(
        email: str, name: str = None, user_id: str = None
    ) -> str:
        """Get existing customer by email or create new one."""
        try:
            # Search for existing customer
            customers = stripe.Customer.search(
                query=f"email:'{email}'", limit=1
            )
            if customers.data:
                return customers.data[0].id

            # Create new customer
            return await StripeService.create_customer(
                email=email,
                name=name,
                metadata={"user_id": user_id} if user_id else None,
            )
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get/create Stripe customer: {e}")
            raise

    @staticmethod
    async def update_customer(
        customer_id: str, email: str = None, name: str = None
    ) -> None:
        """Update customer details."""
        try:
            update_data = {}
            if email:
                update_data["email"] = email
            if name:
                update_data["name"] = name

            if update_data:
                stripe.Customer.modify(customer_id, **update_data)
                logger.info(f"Updated Stripe customer: {customer_id}")
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe customer: {e}")
            raise

    # ============== Payment Methods ==============

    @staticmethod
    async def create_setup_intent(customer_id: str) -> dict:
        """Create a SetupIntent to save a payment method."""
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=["card"],
            )
            logger.info(f"Created SetupIntent: {setup_intent.id}")
            return {
                "id": setup_intent.id,
                "client_secret": setup_intent.client_secret,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create SetupIntent: {e}")
            raise

    @staticmethod
    async def list_payment_methods(customer_id: str) -> list[dict]:
        """List saved payment methods for a customer."""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id, type="card"
            )
            return [
                {
                    "id": pm.id,
                    "brand": pm.card.brand,
                    "last4": pm.card.last4,
                    "exp_month": pm.card.exp_month,
                    "exp_year": pm.card.exp_year,
                }
                for pm in payment_methods.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list payment methods: {e}")
            raise

    @staticmethod
    async def detach_payment_method(payment_method_id: str) -> None:
        """Detach a payment method from a customer."""
        try:
            stripe.PaymentMethod.detach(payment_method_id)
            logger.info(f"Detached payment method: {payment_method_id}")
        except stripe.error.StripeError as e:
            logger.error(f"Failed to detach payment method: {e}")
            raise

    # ============== One-Time Payments ==============

    @staticmethod
    async def create_payment_intent(
        amount: int,  # Amount in cents
        customer_id: str,
        payment_method_id: str = None,
        metadata: dict = None,
        description: str = None,
    ) -> dict:
        """Create a PaymentIntent for one-time payment."""
        try:
            intent_params = {
                "amount": amount,
                "currency": "usd",
                "customer": customer_id,
                "metadata": metadata or {},
            }

            if payment_method_id:
                intent_params["payment_method"] = payment_method_id
                intent_params["confirm"] = True
                intent_params["return_url"] = settings.FRONTEND_URL + "/payment/complete"

            if description:
                intent_params["description"] = description

            payment_intent = stripe.PaymentIntent.create(**intent_params)
            logger.info(f"Created PaymentIntent: {payment_intent.id}")

            return {
                "id": payment_intent.id,
                "client_secret": payment_intent.client_secret,
                "status": payment_intent.status,
                "amount": payment_intent.amount,
            }
        except stripe.error.CardError as e:
            logger.error(f"Card error: {e.user_message}")
            raise
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create PaymentIntent: {e}")
            raise

    @staticmethod
    async def confirm_payment_intent(
        payment_intent_id: str, payment_method_id: str
    ) -> dict:
        """Confirm a PaymentIntent with a payment method."""
        try:
            payment_intent = stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method=payment_method_id,
                return_url=settings.FRONTEND_URL + "/payment/complete",
            )
            return {
                "id": payment_intent.id,
                "status": payment_intent.status,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to confirm PaymentIntent: {e}")
            raise

    @staticmethod
    async def get_payment_intent(payment_intent_id: str) -> dict:
        """Get PaymentIntent details."""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "id": payment_intent.id,
                "status": payment_intent.status,
                "amount": payment_intent.amount,
                "metadata": payment_intent.metadata,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve PaymentIntent: {e}")
            raise

    # ============== Subscriptions ==============

    @staticmethod
    async def create_subscription(
        customer_id: str,
        price_id: str,
        payment_method_id: str,
        metadata: dict = None,
    ) -> dict:
        """Create a subscription for recurring billing."""
        try:
            # Set default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={"default_payment_method": payment_method_id},
            )

            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                metadata=metadata or {},
                expand=["latest_invoice.payment_intent"],
            )

            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise

    @staticmethod
    async def cancel_subscription(subscription_id: str) -> dict:
        """Cancel a subscription."""
        try:
            subscription = stripe.Subscription.cancel(subscription_id)
            logger.info(f"Cancelled subscription: {subscription_id}")
            return {
                "id": subscription.id,
                "status": subscription.status,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise

    # ============== Installments ==============

    @staticmethod
    async def create_installment_subscription(
        customer_id: str,
        amount_cents: int,
        num_installments: int,
        interval: str,  # "week" or "month"
        payment_method_id: str,
        metadata: dict = None,
    ) -> dict:
        """
        Create an installment plan using subscription with iterations.

        Note: This creates a subscription that auto-cancels after num_installments.
        """
        try:
            # Set default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={"default_payment_method": payment_method_id},
            )

            # Create a price for the installment
            price = stripe.Price.create(
                unit_amount=amount_cents,
                currency="usd",
                recurring={"interval": interval},
                product_data={"name": "Installment Payment"},
            )

            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price.id}],
                cancel_at_period_end=False,
                metadata={
                    **(metadata or {}),
                    "installment_plan": "true",
                    "total_installments": str(num_installments),
                },
            )

            # Schedule cancellation after all installments
            # This is handled via webhook tracking

            return {
                "id": subscription.id,
                "status": subscription.status,
                "price_id": price.id,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create installment subscription: {e}")
            raise

    # ============== Refunds ==============

    @staticmethod
    async def create_refund(
        payment_intent_id: str, amount_cents: int = None
    ) -> dict:
        """Create a refund for a payment."""
        try:
            refund_params = {"payment_intent": payment_intent_id}
            if amount_cents:
                refund_params["amount"] = amount_cents

            refund = stripe.Refund.create(**refund_params)
            logger.info(f"Created refund: {refund.id}")

            return {
                "id": refund.id,
                "status": refund.status,
                "amount": refund.amount,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create refund: {e}")
            raise

    # ============== Webhook ==============

    @staticmethod
    def construct_event(payload: bytes, sig_header: str) -> stripe.Event:
        """Construct and verify a Stripe webhook event."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise

    # ============== Utilities ==============

    @staticmethod
    def dollars_to_cents(amount: Decimal) -> int:
        """Convert dollar amount to cents for Stripe."""
        return int(amount * 100)

    @staticmethod
    def cents_to_dollars(amount: int) -> Decimal:
        """Convert cents to dollar amount."""
        return Decimal(amount) / Decimal(100)


# Singleton instance
stripe_service = StripeService()
