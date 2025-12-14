"""Stripe Product and Price management service for admins."""

from decimal import Decimal
from typing import List, Optional, Dict

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_ import Class, BillingModel
from core.config import config as settings
from core.logging import get_logger

logger = get_logger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeProductService:
    """Service for managing Stripe Products and Prices."""

    # ============== Product Management ==============

    @staticmethod
    async def create_product(
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> dict:
        """
        Create a Stripe Product.

        Args:
            name: Product name
            description: Product description
            metadata: Additional metadata

        Returns:
            Product data dict

        Raises:
            stripe.error.StripeError: If product creation fails
        """
        try:
            product = stripe.Product.create(
                name=name,
                description=description,
                metadata=metadata or {},
            )
            logger.info(f"Created Stripe product: {product.id}")
            return {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "metadata": product.metadata,
                "created": product.created,
                "active": product.active,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe product: {e}")
            raise

    @staticmethod
    async def update_product(
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        active: Optional[bool] = None,
    ) -> dict:
        """
        Update a Stripe Product.

        Args:
            product_id: Stripe Product ID
            name: New product name
            description: New description
            metadata: New metadata
            active: Active status

        Returns:
            Updated product data

        Raises:
            stripe.error.StripeError: If update fails
        """
        try:
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if metadata is not None:
                update_data["metadata"] = metadata
            if active is not None:
                update_data["active"] = active

            product = stripe.Product.modify(product_id, **update_data)
            logger.info(f"Updated Stripe product: {product_id}")
            return {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "metadata": product.metadata,
                "active": product.active,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe product: {e}")
            raise

    @staticmethod
    async def delete_product(product_id: str) -> bool:
        """
        Delete (archive) a Stripe Product.

        Args:
            product_id: Stripe Product ID

        Returns:
            True if deleted

        Raises:
            stripe.error.StripeError: If deletion fails
        """
        try:
            product = stripe.Product.modify(product_id, active=False)
            logger.info(f"Archived Stripe product: {product_id}")
            return product.active == False
        except stripe.error.StripeError as e:
            logger.error(f"Failed to archive Stripe product: {e}")
            raise

    @staticmethod
    async def get_product(product_id: str) -> dict:
        """
        Get a Stripe Product.

        Args:
            product_id: Stripe Product ID

        Returns:
            Product data

        Raises:
            stripe.error.StripeError: If retrieval fails
        """
        try:
            product = stripe.Product.retrieve(product_id)
            return {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "metadata": product.metadata,
                "active": product.active,
                "created": product.created,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve Stripe product: {e}")
            raise

    @staticmethod
    async def list_products(
        limit: int = 100,
        active: Optional[bool] = None,
    ) -> List[dict]:
        """
        List Stripe Products.

        Args:
            limit: Max number to return
            active: Filter by active status

        Returns:
            List of product data

        Raises:
            stripe.error.StripeError: If listing fails
        """
        try:
            params = {"limit": limit}
            if active is not None:
                params["active"] = active

            products = stripe.Product.list(**params)
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "metadata": p.metadata,
                    "active": p.active,
                    "created": p.created,
                }
                for p in products.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list Stripe products: {e}")
            raise

    # ============== Price Management ==============

    @staticmethod
    async def create_price(
        product_id: str,
        amount: Decimal,
        currency: str = "usd",
        interval: str = "month",  # month, year
        interval_count: int = 1,
        metadata: Optional[Dict] = None,
    ) -> dict:
        """
        Create a Stripe Price for a Product.

        Args:
            product_id: Stripe Product ID
            amount: Price amount in dollars
            currency: Currency code
            interval: Billing interval (month, year)
            interval_count: Number of intervals (e.g., 3 for quarterly)
            metadata: Additional metadata

        Returns:
            Price data dict

        Raises:
            stripe.error.StripeError: If price creation fails
        """
        try:
            # Convert dollars to cents
            unit_amount = int(amount * 100)

            price = stripe.Price.create(
                product=product_id,
                unit_amount=unit_amount,
                currency=currency,
                recurring={
                    "interval": interval,
                    "interval_count": interval_count,
                },
                metadata=metadata or {},
            )
            logger.info(f"Created Stripe price: {price.id} for product {product_id}")
            return {
                "id": price.id,
                "product": price.product,
                "amount": Decimal(price.unit_amount) / 100,
                "currency": price.currency,
                "interval": price.recurring.interval if price.recurring else None,
                "interval_count": price.recurring.interval_count if price.recurring else None,
                "metadata": price.metadata,
                "active": price.active,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe price: {e}")
            raise

    @staticmethod
    async def create_one_time_price(
        product_id: str,
        amount: Decimal,
        currency: str = "usd",
        metadata: Optional[Dict] = None,
    ) -> dict:
        """
        Create a one-time Stripe Price (no recurring).

        Args:
            product_id: Stripe Product ID
            amount: Price amount in dollars
            currency: Currency code
            metadata: Additional metadata

        Returns:
            Price data dict

        Raises:
            stripe.error.StripeError: If price creation fails
        """
        try:
            # Convert dollars to cents
            unit_amount = int(amount * 100)

            price = stripe.Price.create(
                product=product_id,
                unit_amount=unit_amount,
                currency=currency,
                metadata=metadata or {},
            )
            logger.info(f"Created one-time Stripe price: {price.id} for product {product_id}")
            return {
                "id": price.id,
                "product": price.product,
                "amount": Decimal(price.unit_amount) / 100,
                "currency": price.currency,
                "metadata": price.metadata,
                "active": price.active,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create one-time Stripe price: {e}")
            raise

    @staticmethod
    async def update_price(
        price_id: str,
        metadata: Optional[Dict] = None,
        active: Optional[bool] = None,
    ) -> dict:
        """
        Update a Stripe Price (limited fields).

        Note: Amount and interval cannot be changed. Create new price instead.

        Args:
            price_id: Stripe Price ID
            metadata: New metadata
            active: Active status

        Returns:
            Updated price data

        Raises:
            stripe.error.StripeError: If update fails
        """
        try:
            update_data = {}
            if metadata is not None:
                update_data["metadata"] = metadata
            if active is not None:
                update_data["active"] = active

            price = stripe.Price.modify(price_id, **update_data)
            logger.info(f"Updated Stripe price: {price_id}")
            return {
                "id": price.id,
                "product": price.product,
                "amount": Decimal(price.unit_amount) / 100,
                "currency": price.currency,
                "interval": price.recurring.interval if price.recurring else None,
                "interval_count": price.recurring.interval_count if price.recurring else None,
                "metadata": price.metadata,
                "active": price.active,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe price: {e}")
            raise

    @staticmethod
    async def deactivate_price(price_id: str) -> bool:
        """
        Deactivate a Stripe Price.

        Args:
            price_id: Stripe Price ID

        Returns:
            True if deactivated

        Raises:
            stripe.error.StripeError: If deactivation fails
        """
        try:
            price = stripe.Price.modify(price_id, active=False)
            logger.info(f"Deactivated Stripe price: {price_id}")
            return price.active == False
        except stripe.error.StripeError as e:
            logger.error(f"Failed to deactivate Stripe price: {e}")
            raise

    @staticmethod
    async def get_price(price_id: str) -> dict:
        """
        Get a Stripe Price.

        Args:
            price_id: Stripe Price ID

        Returns:
            Price data

        Raises:
            stripe.error.StripeError: If retrieval fails
        """
        try:
            price = stripe.Price.retrieve(price_id)
            return {
                "id": price.id,
                "product": price.product,
                "amount": Decimal(price.unit_amount) / 100,
                "currency": price.currency,
                "interval": price.recurring.interval if price.recurring else None,
                "interval_count": price.recurring.interval_count if price.recurring else None,
                "metadata": price.metadata,
                "active": price.active,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve Stripe price: {e}")
            raise

    @staticmethod
    async def list_prices(
        product_id: Optional[str] = None,
        limit: int = 100,
        active: Optional[bool] = None,
    ) -> List[dict]:
        """
        List Stripe Prices.

        Args:
            product_id: Filter by product ID
            limit: Max number to return
            active: Filter by active status

        Returns:
            List of price data

        Raises:
            stripe.error.StripeError: If listing fails
        """
        try:
            params = {"limit": limit}
            if product_id:
                params["product"] = product_id
            if active is not None:
                params["active"] = active

            prices = stripe.Price.list(**params)
            return [
                {
                    "id": p.id,
                    "product": p.product,
                    "amount": Decimal(p.unit_amount) / 100,
                    "currency": p.currency,
                    "interval": p.recurring.interval if p.recurring else None,
                    "interval_count": p.recurring.interval_count if p.recurring else None,
                    "metadata": p.metadata,
                    "active": p.active,
                }
                for p in prices.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list Stripe prices: {e}")
            raise

    # ============== Class Integration ==============

    @staticmethod
    async def create_product_for_class(
        db_session: AsyncSession,
        class_id: str,
    ) -> dict:
        """
        Create a Stripe Product for a class and update class record.

        Args:
            db_session: Database session
            class_id: Class ID

        Returns:
            Product and price data

        Raises:
            ValueError: If class not found
            stripe.error.StripeError: If Stripe operation fails
        """
        # Get class
        class_ = await Class.get_by_id(db_session, class_id)
        if not class_:
            raise ValueError(f"Class {class_id} not found")

        # Create product
        product = await StripeProductService.create_product(
            name=class_.name,
            description=class_.description,
            metadata={
                "class_id": class_id,
                "program_id": class_.program_id,
                "school_id": class_.school_id or "",
            },
        )

        # Update class with product ID
        class_.stripe_product_id = product["id"]
        await db_session.commit()

        logger.info(f"Linked Stripe product {product['id']} to class {class_id}")

        return product

    @staticmethod
    async def create_prices_for_class(
        db_session: AsyncSession,
        class_id: str,
        create_monthly: bool = False,
        create_quarterly: bool = False,
        create_annual: bool = False,
    ) -> Dict[str, dict]:
        """
        Create Stripe Prices for a class based on configured pricing.

        Args:
            db_session: Database session
            class_id: Class ID
            create_monthly: Create monthly price
            create_quarterly: Create quarterly price
            create_annual: Create annual price

        Returns:
            Dict of created prices by interval

        Raises:
            ValueError: If class not found or product not created
            stripe.error.StripeError: If Stripe operation fails
        """
        # Get class
        class_ = await Class.get_by_id(db_session, class_id)
        if not class_:
            raise ValueError(f"Class {class_id} not found")

        if not class_.stripe_product_id:
            raise ValueError(f"Class {class_id} has no Stripe product. Create product first.")

        created_prices = {}

        # Create monthly price
        if create_monthly and class_.monthly_price:
            monthly_price = await StripeProductService.create_price(
                product_id=class_.stripe_product_id,
                amount=class_.monthly_price,
                interval="month",
                interval_count=1,
                metadata={"class_id": class_id, "billing_model": "monthly"},
            )
            class_.stripe_monthly_price_id = monthly_price["id"]
            created_prices["monthly"] = monthly_price

        # Create quarterly price
        if create_quarterly and class_.quarterly_price:
            quarterly_price = await StripeProductService.create_price(
                product_id=class_.stripe_product_id,
                amount=class_.quarterly_price,
                interval="month",
                interval_count=3,
                metadata={"class_id": class_id, "billing_model": "quarterly"},
            )
            class_.stripe_quarterly_price_id = quarterly_price["id"]
            created_prices["quarterly"] = quarterly_price

        # Create annual price
        if create_annual and class_.annual_price:
            annual_price = await StripeProductService.create_price(
                product_id=class_.stripe_product_id,
                amount=class_.annual_price,
                interval="year",
                interval_count=1,
                metadata={"class_id": class_id, "billing_model": "annual"},
            )
            class_.stripe_annual_price_id = annual_price["id"]
            created_prices["annual"] = annual_price

        await db_session.commit()

        logger.info(f"Created {len(created_prices)} price(s) for class {class_id}")

        return created_prices

    @staticmethod
    async def sync_class_with_stripe(
        db_session: AsyncSession,
        class_id: str,
    ) -> dict:
        """
        Create Stripe Product and Prices for a class in one operation.

        Args:
            db_session: Database session
            class_id: Class ID

        Returns:
            Dict with product and prices

        Raises:
            ValueError: If class not found
            stripe.error.StripeError: If Stripe operation fails
        """
        # Get class
        class_ = await Class.get_by_id(db_session, class_id)
        if not class_:
            raise ValueError(f"Class {class_id} not found")

        # Create product if not exists
        if not class_.stripe_product_id:
            product = await StripeProductService.create_product_for_class(
                db_session, class_id
            )
        else:
            product = await StripeProductService.get_product(class_.stripe_product_id)

        # Create prices based on billing model
        prices = {}
        if class_.is_subscription_based:
            if class_.billing_model == BillingModel.MONTHLY and class_.monthly_price:
                prices = await StripeProductService.create_prices_for_class(
                    db_session, class_id, create_monthly=True
                )
            elif class_.billing_model == BillingModel.QUARTERLY and class_.quarterly_price:
                prices = await StripeProductService.create_prices_for_class(
                    db_session, class_id, create_quarterly=True
                )
            elif class_.billing_model == BillingModel.ANNUAL and class_.annual_price:
                prices = await StripeProductService.create_prices_for_class(
                    db_session, class_id, create_annual=True
                )

        return {
            "product": product,
            "prices": prices,
        }

    @staticmethod
    async def process_payment_options(
        db_session: AsyncSession,
        class_: Class,
        payment_options: List[Dict],
    ) -> Dict[str, Dict]:
        """
        Process payment options and create Stripe Products/Prices.

        This method:
        1. Creates/gets Stripe Product for the class
        2. Creates Stripe Prices for each payment option
        3. Returns mapping of payment option names to Stripe Price data

        Args:
            db_session: Database session
            class_: Class instance
            payment_options: List of payment option dicts with:
                - name: Display name
                - type: "one_time" or "recurring"
                - amount: Decimal amount
                - interval: "month" or "year" (for recurring)
                - interval_count: Number of intervals (default: 1)
                - description: Optional description

        Returns:
            Dict mapping payment option names to created Price data:
            {
                "Monthly Membership": {
                    "id": "price_xyz",
                    "amount": 9900,
                    "type": "recurring",
                    ...
                },
                ...
            }

        Raises:
            ValueError: If validation fails
            stripe.error.StripeError: If Stripe operation fails
        """
        logger.info(
            f"Processing {len(payment_options)} payment options for class {class_.id}"
        )

        # Step 1: Create or get Stripe Product
        if not class_.stripe_product_id:
            logger.info(f"Creating Stripe product for class {class_.id}")
            product = await StripeProductService.create_product(
                name=f"{class_.name}",
                description=class_.description,
                metadata={
                    "class_id": str(class_.id),
                    "class_name": class_.name,
                    "program_id": str(class_.program_id),
                },
            )
            class_.stripe_product_id = product["id"]
            await db_session.commit()
            logger.info(f"Created Stripe product {product['id']} for class {class_.id}")
        else:
            logger.info(f"Using existing Stripe product {class_.stripe_product_id}")

        # Step 2: Create Stripe Prices for each payment option
        created_prices = {}

        for idx, option in enumerate(payment_options):
            option_name = option.get("name", f"Option {idx + 1}")
            option_type = option["type"]
            amount = option["amount"]
            interval = option.get("interval")
            interval_count = option.get("interval_count", 1)
            description = option.get("description")

            logger.info(
                f"Creating Stripe price for payment option '{option_name}' "
                f"(type: {option_type}, amount: ${amount})"
            )

            try:
                if option_type == "recurring":
                    # Create recurring price
                    if not interval:
                        raise ValueError(
                            f"Payment option '{option_name}': interval is required for recurring payments"
                        )

                    price = await StripeProductService.create_price(
                        product_id=class_.stripe_product_id,
                        amount=Decimal(str(amount)),
                        currency="usd",
                        interval=interval,
                        interval_count=interval_count,
                        metadata={
                            "class_id": str(class_.id),
                            "payment_option_name": option_name,
                            "payment_option_type": option_type,
                        },
                    )
                else:
                    # Create one-time price
                    price = await StripeProductService.create_one_time_price(
                        product_id=class_.stripe_product_id,
                        amount=Decimal(str(amount)),
                        currency="usd",
                        metadata={
                            "class_id": str(class_.id),
                            "payment_option_name": option_name,
                            "payment_option_type": option_type,
                        },
                    )

                # Add additional info to the price data
                price["payment_option_name"] = option_name
                price["payment_option_type"] = option_type
                if description:
                    price["payment_option_description"] = description

                created_prices[option_name] = price

                logger.info(
                    f"Created Stripe price {price['id']} for payment option '{option_name}'"
                )

            except Exception as e:
                logger.error(
                    f"Failed to create Stripe price for payment option '{option_name}': {e}"
                )
                raise ValueError(
                    f"Failed to create Stripe price for '{option_name}': {str(e)}"
                )

        logger.info(
            f"Successfully created {len(created_prices)} Stripe prices for class {class_.id}"
        )

        return created_prices
