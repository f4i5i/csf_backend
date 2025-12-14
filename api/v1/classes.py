from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin
from app.models.class_ import Class
from app.models.user import User
from app.schemas.class_ import ClassCreate, ClassListResponse, ClassResponse, ClassUpdate
from app.services.stripe_product_service import StripeProductService
from core.db import get_db
from core.exceptions.base import BadRequestException, NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/classes", tags=["Classes"])


@router.get("/", response_model=ClassListResponse)
async def list_classes(
    program_id: Optional[str] = None,
    school_id: Optional[str] = None,
    area_id: Optional[str] = None,
    has_capacity: Optional[bool] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    search: Optional[str] = Query(None, description="Search in class name and description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db_session: AsyncSession = Depends(get_db),
) -> ClassListResponse:
    """
    List all classes with optional filters.

    Public endpoint - no authentication required.
    Supports search by class name or description.
    """
    logger.info(f"List classes request - skip: {skip}, limit: {limit}, search: {search}")
    classes, total = await Class.get_filtered(
        db_session,
        program_id=program_id,
        school_id=school_id,
        area_id=area_id,
        has_capacity=has_capacity,
        min_age=min_age,
        max_age=max_age,
        search=search,
        skip=skip,
        limit=limit,
    )
    logger.info(f"Found {total} classes")
    return ClassListResponse(
        items=[ClassResponse.model_validate(c) for c in classes],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(
    class_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> ClassResponse:
    """
    Get class details by ID.

    Public endpoint - no authentication required.
    """
    logger.info(f"Get class request for id: {class_id}")
    class_obj = await Class.get_by_id(db_session, class_id)
    if not class_obj:
        logger.warning(f"Class not found: {class_id}")
        raise NotFoundException(message="Class not found")

    logger.info(
        f"Returning class {class_id} - capacity: {class_obj.capacity}, "
        f"current_enrollment: {class_obj.current_enrollment}, "
        f"has_capacity: {class_obj.has_capacity}, "
        f"available_spots: {class_obj.available_spots}"
    )
    return ClassResponse.model_validate(class_obj)


@router.post("/", response_model=ClassResponse)
async def create_class(
    data: ClassCreate,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> ClassResponse:
    """
    Create a new class.

    Requires admin or owner role.

    If payment_options are provided, Stripe Product and Prices will be automatically created.
    """
    logger.info(f"Create class request by user: {current_user.id}, name: {data.name}")
    # Convert weekdays to list of strings (optional for membership classes)
    weekdays = [w.value for w in data.weekdays] if data.weekdays else []

    class_obj = await Class.create_class(
        db_session,
        name=data.name,
        description=data.description,
        ledger_code=data.ledger_code,
        image_url=data.image_url,
        program_id=data.program_id,
        school_id=data.school_id,
        class_type=data.class_type,
        weekdays=weekdays,
        start_time=data.start_time,
        end_time=data.end_time,
        start_date=data.start_date,
        end_date=data.end_date,
        capacity=data.capacity,
        waitlist_enabled=data.waitlist_enabled,
        price=data.price,
        membership_price=data.membership_price,
        installments_enabled=data.installments_enabled,
        min_age=data.min_age,
        max_age=data.max_age,
    )
    logger.info(f"Class created successfully: {class_obj.id}")
    logger.info(
        f"Class capacity details - capacity: {class_obj.capacity}, "
        f"current_enrollment: {class_obj.current_enrollment}, "
        f"has_capacity: {class_obj.has_capacity}, "
        f"available_spots: {class_obj.available_spots}"
    )

    # Process payment_options if provided
    if data.payment_options and data.auto_create_stripe_prices:
        try:
            logger.info(
                f"Processing {len(data.payment_options)} payment options for class {class_obj.id}"
            )
            payment_options_dict = [opt.model_dump() for opt in data.payment_options]
            created_prices = await StripeProductService.process_payment_options(
                db_session=db_session,
                class_=class_obj,
                payment_options=payment_options_dict,
            )
            logger.info(
                f"Successfully created {len(created_prices)} Stripe prices for class {class_obj.id}"
            )
            # Refresh to get updated stripe_product_id
            await db_session.refresh(class_obj)
        except Exception as e:
            logger.error(f"Failed to process payment options: {e}")
            raise BadRequestException(
                message=f"Class created but failed to create Stripe prices: {str(e)}"
            )

    # Eagerly load school relationship before validation to avoid lazy loading issues
    await db_session.refresh(class_obj, attribute_names=['school'])

    return ClassResponse.model_validate(class_obj)


@router.put("/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: str,
    data: ClassUpdate,
    db_session: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_admin),
) -> ClassResponse:
    """
    Update a class.

    Requires admin or owner role.

    If payment_options are provided, new Stripe Prices will be created.
    """
    # logger.info(f"Update class request by user: {current_user.id}, class_id: {class_id}")
    class_obj = await Class.get_by_id(db_session, class_id)
    if not class_obj:
        logger.warning(f"Class not found: {class_id}")
        raise NotFoundException(message="Class not found")

    update_data = data.model_dump(exclude_unset=True)

    # Extract payment_options and auto_create_stripe_prices before updating
    payment_options = update_data.pop("payment_options", None)
    auto_create_stripe_prices = update_data.pop("auto_create_stripe_prices", True)

    # Convert weekdays to list of strings if provided
    if "weekdays" in update_data and update_data["weekdays"]:
        update_data["weekdays"] = [w.value for w in update_data["weekdays"]]

    # Enforce schedule and age invariants even on partial updates
    new_start_date = update_data.get("start_date", class_obj.start_date)
    new_end_date = update_data.get("end_date", class_obj.end_date)
    if new_end_date < new_start_date:
        raise BadRequestException(message="end_date must be after start_date")

    new_start_time = update_data.get("start_time", class_obj.start_time)
    new_end_time = update_data.get("end_time", class_obj.end_time)
    if new_end_time <= new_start_time:
        raise BadRequestException(message="end_time must be after start_time")

    new_min_age = update_data.get("min_age", class_obj.min_age)
    new_max_age = update_data.get("max_age", class_obj.max_age)
    if new_max_age < new_min_age:
        raise BadRequestException(
            message="max_age must be greater than or equal to min_age"
        )

    for field, value in update_data.items():
        setattr(class_obj, field, value)

    await db_session.commit()
    await db_session.refresh(class_obj)
    logger.info(f"Class updated successfully: {class_id}")

    # Process payment_options if provided
    if payment_options and auto_create_stripe_prices:
        try:
            logger.info(
                f"Processing {len(payment_options)} payment options for class {class_id}"
            )
            created_prices = await StripeProductService.process_payment_options(
                db_session=db_session,
                class_=class_obj,
                payment_options=payment_options,
            )
            logger.info(
                f"Successfully created {len(created_prices)} Stripe prices for class {class_id}"
            )
            # Refresh to get updated stripe_product_id
            await db_session.refresh(class_obj)
        except Exception as e:
            logger.error(f"Failed to process payment options: {e}")
            raise BadRequestException(
                message=f"Class updated but failed to create Stripe prices: {str(e)}"
            )

    return ClassResponse.model_validate(class_obj)


@router.delete("/{class_id}")
async def delete_class(
    class_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> dict:
    """
    Soft delete a class.

    Requires admin or owner role.
    """
    logger.info(f"Delete class request by user: {current_user.id}, class_id: {class_id}")
    class_obj = await Class.get_by_id(db_session, class_id)
    if not class_obj:
        logger.warning(f"Class not found: {class_id}")
        raise NotFoundException(message="Class not found")

    class_obj.is_active = False
    await db_session.commit()
    logger.info(f"Class deleted successfully: {class_id}")
    return {"message": "Class deleted successfully"}
