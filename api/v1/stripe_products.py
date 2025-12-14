"""Admin endpoints for Stripe Product and Price management."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_admin
from app.models.user import User
from app.schemas.stripe_product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    PriceCreate,
    OneTimePriceCreate,
    PriceUpdate,
    PriceResponse,
    ClassProductCreate,
    ClassPricesCreate,
    ClassProductSyncRequest,
    ClassProductSyncResponse,
)
from app.services.stripe_product_service import StripeProductService
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/stripe", tags=["Admin - Stripe Products"])


# ============== Product Management ==============


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_admin),
):
    """
    Create a new Stripe Product.

    **Admin only**
    """
    try:
        product = await StripeProductService.create_product(
            name=data.name,
            description=data.description,
            metadata=data.metadata,
        )
        return product
    except Exception as e:
        logger.error(f"Failed to create product: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create product: {str(e)}",
        )


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    active: Optional[bool] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
):
    """
    List all Stripe Products.

    **Admin only**
    """
    try:
        products = await StripeProductService.list_products(
            limit=limit,
            active=active,
        )
        return products
    except Exception as e:
        logger.error(f"Failed to list products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list products: {str(e)}",
        )


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_admin),
):
    """
    Get a Stripe Product by ID.

    **Admin only**
    """
    try:
        product = await StripeProductService.get_product(product_id)
        return product
    except Exception as e:
        logger.error(f"Failed to get product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {str(e)}",
        )


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    current_user: User = Depends(get_current_admin),
):
    """
    Update a Stripe Product.

    **Admin only**
    """
    try:
        product = await StripeProductService.update_product(
            product_id=product_id,
            name=data.name,
            description=data.description,
            metadata=data.metadata,
            active=data.active,
        )
        return product
    except Exception as e:
        logger.error(f"Failed to update product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update product: {str(e)}",
        )


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_admin),
):
    """
    Archive a Stripe Product (sets active=false).

    **Admin only**
    """
    try:
        await StripeProductService.delete_product(product_id)
        return None
    except Exception as e:
        logger.error(f"Failed to archive product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to archive product: {str(e)}",
        )


# ============== Price Management ==============


@router.post("/prices", response_model=PriceResponse, status_code=status.HTTP_201_CREATED)
async def create_price(
    data: PriceCreate,
    current_user: User = Depends(get_current_admin),
):
    """
    Create a new recurring Stripe Price.

    **Admin only**
    """
    try:
        price = await StripeProductService.create_price(
            product_id=data.product_id,
            amount=data.amount,
            currency=data.currency,
            interval=data.interval,
            interval_count=data.interval_count,
            metadata=data.metadata,
        )
        return price
    except Exception as e:
        logger.error(f"Failed to create price: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create price: {str(e)}",
        )


@router.post("/prices/one-time", response_model=PriceResponse, status_code=status.HTTP_201_CREATED)
async def create_one_time_price(
    data: OneTimePriceCreate,
    current_user: User = Depends(get_current_admin),
):
    """
    Create a one-time Stripe Price (no recurring).

    **Admin only**
    """
    try:
        price = await StripeProductService.create_one_time_price(
            product_id=data.product_id,
            amount=data.amount,
            currency=data.currency,
            metadata=data.metadata,
        )
        return price
    except Exception as e:
        logger.error(f"Failed to create one-time price: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create one-time price: {str(e)}",
        )


@router.get("/prices", response_model=List[PriceResponse])
async def list_prices(
    product_id: Optional[str] = None,
    active: Optional[bool] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
):
    """
    List Stripe Prices, optionally filtered by product.

    **Admin only**
    """
    try:
        prices = await StripeProductService.list_prices(
            product_id=product_id,
            limit=limit,
            active=active,
        )
        return prices
    except Exception as e:
        logger.error(f"Failed to list prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list prices: {str(e)}",
        )


@router.get("/prices/{price_id}", response_model=PriceResponse)
async def get_price(
    price_id: str,
    current_user: User = Depends(get_current_admin),
):
    """
    Get a Stripe Price by ID.

    **Admin only**
    """
    try:
        price = await StripeProductService.get_price(price_id)
        return price
    except Exception as e:
        logger.error(f"Failed to get price {price_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Price not found: {str(e)}",
        )


@router.put("/prices/{price_id}", response_model=PriceResponse)
async def update_price(
    price_id: str,
    data: PriceUpdate,
    current_user: User = Depends(get_current_admin),
):
    """
    Update a Stripe Price (metadata and active status only).

    Note: Amount and interval cannot be changed. Create a new price instead.

    **Admin only**
    """
    try:
        price = await StripeProductService.update_price(
            price_id=price_id,
            metadata=data.metadata,
            active=data.active,
        )
        return price
    except Exception as e:
        logger.error(f"Failed to update price {price_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update price: {str(e)}",
        )


@router.delete("/prices/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_price(
    price_id: str,
    current_user: User = Depends(get_current_admin),
):
    """
    Deactivate a Stripe Price (sets active=false).

    **Admin only**
    """
    try:
        await StripeProductService.deactivate_price(price_id)
        return None
    except Exception as e:
        logger.error(f"Failed to deactivate price {price_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to deactivate price: {str(e)}",
        )


# ============== Class Integration ==============


@router.post("/classes/product", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product_for_class(
    data: ClassProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Create a Stripe Product for a class and link it.

    **Admin only**
    """
    try:
        product = await StripeProductService.create_product_for_class(
            db_session=db,
            class_id=data.class_id,
        )
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create product for class: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create product for class: {str(e)}",
        )


@router.post("/classes/prices", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_prices_for_class(
    data: ClassPricesCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Create Stripe Prices for a class based on configured pricing.

    **Admin only**
    """
    try:
        prices = await StripeProductService.create_prices_for_class(
            db_session=db,
            class_id=data.class_id,
            create_monthly=data.create_monthly,
            create_quarterly=data.create_quarterly,
            create_annual=data.create_annual,
        )
        return {"prices": prices}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create prices for class: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create prices for class: {str(e)}",
        )


@router.post("/classes/sync", response_model=dict, status_code=status.HTTP_200_OK)
async def sync_class_with_stripe(
    data: ClassProductSyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Create Stripe Product and Prices for a class in one operation.

    This automatically creates the product (if needed) and prices based on
    the class's billing model and configured prices.

    **Admin only**
    """
    try:
        result = await StripeProductService.sync_class_with_stripe(
            db_session=db,
            class_id=data.class_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to sync class with Stripe: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync class with Stripe: {str(e)}",
        )
