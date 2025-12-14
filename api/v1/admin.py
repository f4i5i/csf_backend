"""Admin API endpoints for dashboard, reports, and client management."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_admin
from app.models.attendance import Attendance
from app.models.child import Child
from app.models.class_ import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus, PaymentType, RefundStatus
from app.models.program import Area, Program, School
from app.models.user import Role, User
from app.schemas.admin import (
    ClassRosterResponse,
    ClientDetailResponse,
    ClientListResponse,
    DashboardMetricsResponse,
    PendingRefundResponse,
    PendingRefundsListResponse,
    RefundApprovalRequest,
    RefundItemResponse,
    RefundSearchResponse,
    RevenueReportResponse,
    RosterStudentResponse,
)
from core.db import get_db
from core.exceptions.base import NotFoundException
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    db_session: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> DashboardMetricsResponse:
    """Get dashboard metrics for admin overview.

    Returns key metrics:
    - Total revenue (all time, this month, this week)
    - Active enrollments
    - Total students
    - Total classes
    - Attendance rate
    - Recent activity counts
    """
    logger.info(f"Fetching dashboard metrics for admin: {current_admin.id}")

    # Date ranges
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = date(today.year, today.month, 1)

    # Total Revenue (paid/completed payments only)
    revenue_all_time = await db_session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.COMPLETED
        )
    )
    total_revenue = float(revenue_all_time.scalar() or 0)

    # Revenue this month
    revenue_month = await db_session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.COMPLETED,
            func.date(Payment.created_at) >= month_start,
        )
    )
    revenue_this_month = float(revenue_month.scalar() or 0)

    # Revenue this week
    revenue_week = await db_session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.COMPLETED,
            func.date(Payment.created_at) >= week_start,
        )
    )
    revenue_this_week = float(revenue_week.scalar() or 0)

    # Active Enrollments
    active_enrollments = await db_session.execute(
        select(func.count(Enrollment.id)).where(
            Enrollment.status == EnrollmentStatus.ACTIVE
        )
    )
    total_active_enrollments = active_enrollments.scalar() or 0

    # Total Students (unique children with active enrollments)
    total_students = await db_session.execute(
        select(func.count(func.distinct(Enrollment.child_id))).where(
            Enrollment.status == EnrollmentStatus.ACTIVE
        )
    )
    total_unique_students = total_students.scalar() or 0

    # Total Active Classes
    total_classes = await db_session.execute(
        select(func.count(Class.id)).where(Class.is_active == True)
    )
    total_active_classes = total_classes.scalar() or 0

    # Attendance Rate (last 30 days)
    attendance_30_days = await db_session.execute(
        select(
            func.count(Attendance.id),
            func.sum(func.case((Attendance.status == "present", 1), else_=0)),
        ).where(Attendance.date >= today - timedelta(days=30))
    )
    attendance_data = attendance_30_days.first()
    total_records = attendance_data[0] or 0
    present_count = attendance_data[1] or 0
    attendance_rate = (present_count / total_records * 100) if total_records > 0 else 0

    # New Enrollments this week
    new_enrollments_week = await db_session.execute(
        select(func.count(Enrollment.id)).where(
            func.date(Enrollment.created_at) >= week_start
        )
    )
    new_enrollments = new_enrollments_week.scalar() or 0

    # Pending Orders
    pending_orders = await db_session.execute(
        select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING)
    )
    pending_order_count = pending_orders.scalar() or 0

    return DashboardMetricsResponse(
        total_revenue=total_revenue,
        revenue_this_month=revenue_this_month,
        revenue_this_week=revenue_this_week,
        active_enrollments=total_active_enrollments,
        total_students=total_unique_students,
        total_classes=total_active_classes,
        attendance_rate=round(attendance_rate, 2),
        new_enrollments_this_week=new_enrollments,
        pending_orders=pending_order_count,
    )


@router.get("/finance/revenue", response_model=RevenueReportResponse)
async def get_revenue_report(
    start_date: Optional[date] = Query(None, description="Start date for report"),
    end_date: Optional[date] = Query(None, description="End date for report"),
    group_by: str = Query("day", description="Group by: day, week, month"),
    db_session: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> RevenueReportResponse:
    """Get revenue report with grouping options.

    Args:
        start_date: Start date (defaults to 30 days ago)
        end_date: End date (defaults to today)
        group_by: Grouping interval (day, week, month)

    Returns:
        Revenue breakdown by time period and payment type
    """
    logger.info(f"Generating revenue report for admin: {current_admin.id}")

    # Default date range: last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Get payments in date range
    stmt = (
        select(
            func.date(Payment.created_at).label("payment_date"),
            Payment.payment_type,
            func.sum(Payment.amount).label("total_amount"),
            func.count(Payment.id).label("payment_count"),
        )
        .where(
            Payment.status == PaymentStatus.COMPLETED,
            func.date(Payment.created_at) >= start_date,
            func.date(Payment.created_at) <= end_date,
        )
        .group_by(func.date(Payment.created_at), Payment.payment_type)
        .order_by(func.date(Payment.created_at))
    )

    result = await db_session.execute(stmt)
    payments = result.all()

    # Format data for response
    revenue_by_date: Dict[str, Dict[str, float]] = {}
    total_by_type = {
        "one_time": 0.0,
        "subscription": 0.0,
        "installment": 0.0,
    }

    for payment_date, payment_type, amount, count in payments:
        date_key = payment_date.isoformat()

        if date_key not in revenue_by_date:
            revenue_by_date[date_key] = {
                "one_time": 0.0,
                "subscription": 0.0,
                "installment": 0.0,
                "total": 0.0,
            }

        payment_type_str = payment_type.value if hasattr(payment_type, "value") else str(payment_type)
        revenue_by_date[date_key][payment_type_str] = float(amount)
        revenue_by_date[date_key]["total"] += float(amount)
        total_by_type[payment_type_str] += float(amount)

    grand_total = sum(total_by_type.values())

    return RevenueReportResponse(
        start_date=start_date,
        end_date=end_date,
        total_revenue=grand_total,
        revenue_by_type=total_by_type,
        revenue_by_date=revenue_by_date,
        group_by=group_by,
    )


@router.get("/clients", response_model=ClientListResponse)
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name or email"),
    has_active_enrollment: Optional[bool] = Query(None),
    program_id: Optional[str] = Query(None),
    db_session: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> ClientListResponse:
    """List all clients (parents) with filters and pagination.

    Filters:
    - search: Search by name or email
    - has_active_enrollment: Filter by active enrollment status
    - program_id: Filter by program enrollment
    """
    logger.info(f"Listing clients for admin: {current_admin.id}")

    # Build query
    stmt = select(User).where(User.role == Role.PARENT)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            (User.full_name.ilike(search_term)) | (User.email.ilike(search_term))
        )

    # Apply enrollment filters if needed
    if has_active_enrollment is not None or program_id:
        stmt = stmt.join(Child, Child.user_id == User.id)
        stmt = stmt.join(Enrollment, Enrollment.child_id == Child.id)

        if has_active_enrollment:
            stmt = stmt.where(Enrollment.status == EnrollmentStatus.ACTIVE)

        if program_id:
            stmt = stmt.join(Class, Class.id == Enrollment.class_id)
            stmt = stmt.where(Class.program_id == program_id)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db_session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply pagination and get results
    stmt = stmt.distinct().offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db_session.execute(stmt)
    clients = result.scalars().all()

    # Format response with basic client info
    items = []
    for client in clients:
        # Count children and enrollments
        children_count = await db_session.execute(
            select(func.count(Child.id)).where(Child.user_id == client.id)
        )

        enrollments_count = await db_session.execute(
            select(func.count(Enrollment.id))
            .join(Child, Child.id == Enrollment.child_id)
            .where(
                Child.user_id == client.id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )

        items.append({
            "id": client.id,
            "email": client.email,
            "full_name": client.full_name,
            "phone": client.phone,
            "children_count": children_count.scalar() or 0,
            "active_enrollments": enrollments_count.scalar() or 0,
            "created_at": client.created_at,
        })

    return ClientListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/clients/{client_id}", response_model=ClientDetailResponse)
async def get_client_detail(
    client_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> ClientDetailResponse:
    """Get detailed information about a specific client.

    Includes:
    - Client info
    - Children
    - Active enrollments
    - Payment history
    - Order history
    """
    logger.info(f"Fetching client detail for {client_id} (admin: {current_admin.id})")

    # Get client
    client = await db_session.get(User, client_id)
    if not client or client.role != Role.PARENT:
        raise NotFoundException(f"Client {client_id} not found")

    # Get children
    children_result = await db_session.execute(
        select(Child).where(Child.user_id == client_id)
    )
    children = children_result.scalars().all()

    # Get active enrollments with class details
    enrollments_result = await db_session.execute(
        select(Enrollment, Class, Child)
        .join(Class, Class.id == Enrollment.class_id)
        .join(Child, Child.id == Enrollment.child_id)
        .where(
            Child.user_id == client_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    enrollments_data = enrollments_result.all()

    # Get payment history
    payments_result = await db_session.execute(
        select(Payment, Order)
        .join(Order, Order.id == Payment.order_id)
        .where(Order.user_id == client_id)
        .order_by(Payment.created_at.desc())
        .limit(10)
    )
    payments = payments_result.all()

    # Calculate total spent
    total_spent_result = await db_session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Order, Order.id == Payment.order_id)
        .where(
            Order.user_id == client_id,
            Payment.status == PaymentStatus.COMPLETED,
        )
    )
    total_spent = float(total_spent_result.scalar() or 0)

    return ClientDetailResponse(
        id=client.id,
        email=client.email,
        full_name=client.full_name,
        phone=client.phone,
        created_at=client.created_at,
        children=[
            {
                "id": child.id,
                "first_name": child.first_name,
                "last_name": child.last_name,
                "date_of_birth": child.date_of_birth,
            }
            for child in children
        ],
        active_enrollments=[
            {
                "id": enrollment.id,
                "child_name": f"{child.first_name} {child.last_name}",
                "class_name": class_.name,
                "start_date": class_.start_date,
                "end_date": class_.end_date,
                "status": enrollment.status.value,
            }
            for enrollment, class_, child in enrollments_data
        ],
        recent_payments=[
            {
                "id": payment.id,
                "amount": float(payment.amount),
                "payment_type": payment.payment_type.value,
                "status": payment.status.value,
                "created_at": payment.created_at,
            }
            for payment, order in payments
        ],
        total_spent=total_spent,
    )


@router.get("/classes/{class_id}/roster", response_model=ClassRosterResponse)
async def get_class_roster(
    class_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> ClassRosterResponse:
    """Get complete roster for a class with student and parent details.

    Returns:
    - Class information
    - All enrolled students with parent contact info
    - Enrollment and payment status for each student
    """
    logger.info(f"Getting roster for class {class_id} by admin: {current_admin.id}")

    # Get class
    class_ = await db_session.get(Class, class_id)
    if not class_:
        raise NotFoundException(f"Class {class_id} not found")

    # Get program and school names
    program = await db_session.get(Program, class_.program_id)
    school = await db_session.get(School, class_.school_id)

    # Get all enrollments for this class
    enrollments_result = await db_session.execute(
        select(Enrollment, Child, User)
        .join(Child, Child.id == Enrollment.child_id)
        .join(User, User.id == Enrollment.user_id)
        .where(
            Enrollment.class_id == class_id,
            Enrollment.status.in_([EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING])
        )
        .order_by(Child.last_name, Child.first_name)
    )
    enrollments_data = enrollments_result.all()

    # Build student roster
    students = []
    for enrollment, child, parent in enrollments_data:
        # Calculate age
        child_age = None
        if child.date_of_birth:
            today = date.today()
            child_age = today.year - child.date_of_birth.year
            if (today.month, today.day) < (child.date_of_birth.month, child.date_of_birth.day):
                child_age -= 1

        # Determine payment status
        payment_status = "pending"
        if enrollment.status == EnrollmentStatus.ACTIVE:
            # Check if there's a paid payment for this enrollment's order
            order_result = await db_session.execute(
                select(Order).where(
                    Order.user_id == enrollment.user_id,
                    Order.status == OrderStatus.PAID
                )
            )
            if order_result.scalar_one_or_none():
                payment_status = "paid"

        students.append(RosterStudentResponse(
            enrollment_id=enrollment.id,
            child_id=child.id,
            child_name=child.full_name,
            child_age=child_age,
            child_dob=child.date_of_birth,
            parent_id=parent.id,
            parent_name=parent.full_name,
            parent_email=parent.email,
            parent_phone=parent.phone,
            enrollment_status=enrollment.status.value,
            enrolled_at=enrollment.enrolled_at,
            payment_status=payment_status,
        ))

    return ClassRosterResponse(
        class_id=class_.id,
        class_name=class_.name,
        program_name=program.name if program else "Unknown",
        school_name=school.name if school else "Unknown",
        start_date=class_.start_date,
        end_date=class_.end_date,
        capacity=class_.capacity,
        current_enrollment=class_.current_enrollment,
        students=students,
    )


@router.get("/refunds/search", response_model=RefundSearchResponse)
async def search_refunds(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = Query(None, description="Filter by refund date (start)"),
    end_date: Optional[date] = Query(None, description="Filter by refund date (end)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum refund amount"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum refund amount"),
    payment_status: Optional[str] = Query(None, description="Payment status filter"),
    db_session: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> RefundSearchResponse:
    """Search and filter refunded payments.

    Filters:
    - Date range (start_date, end_date) - filters by payment created_at
    - User ID - filter refunds for specific user
    - Amount range (min_amount, max_amount) - filters by refund_amount
    - Payment status - filter by payment status (refunded, partially_refunded)

    Returns:
    - Paginated list of refunds with order and user details
    - Total count and sum of refunds
    """
    logger.info(f"Searching refunds by admin: {current_admin.id}")

    from decimal import Decimal
    from sqlalchemy.orm import joinedload

    # Build base query - only payments with refund_amount > 0
    stmt = (
        select(Payment)
        .options(
            joinedload(Payment.order),
            joinedload(Payment.user)
        )
        .where(Payment.refund_amount > 0)
    )

    # Apply date range filter
    if start_date:
        stmt = stmt.where(func.date(Payment.created_at) >= start_date)
    if end_date:
        stmt = stmt.where(func.date(Payment.created_at) <= end_date)

    # Apply user filter
    if user_id:
        stmt = stmt.where(Payment.user_id == user_id)

    # Apply amount range filter
    if min_amount is not None:
        stmt = stmt.where(Payment.refund_amount >= Decimal(str(min_amount)))
    if max_amount is not None:
        stmt = stmt.where(Payment.refund_amount <= Decimal(str(max_amount)))

    # Apply status filter
    if payment_status:
        if payment_status.lower() == "refunded":
            stmt = stmt.where(Payment.status == PaymentStatus.REFUNDED)
        elif payment_status.lower() == "partially_refunded":
            stmt = stmt.where(Payment.status == PaymentStatus.PARTIALLY_REFUNDED)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db_session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Get total refunded amount for the filtered results
    sum_stmt = select(func.coalesce(func.sum(Payment.refund_amount), 0)).select_from(stmt.subquery())
    sum_result = await db_session.execute(sum_stmt)
    total_refunded = float(sum_result.scalar() or 0)

    # Apply pagination and get results
    stmt = stmt.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
    result = await db_session.execute(stmt)
    payments = result.scalars().all()

    # Format response with order details
    items = []
    for payment in payments:
        # Get order line items with class/enrollment info
        order_items = []
        if payment.order:
            from app.models.order import OrderLineItem
            line_items_result = await db_session.execute(
                select(OrderLineItem, Class)
                .outerjoin(Enrollment, Enrollment.id == OrderLineItem.enrollment_id)
                .outerjoin(Class, Class.id == Enrollment.class_id)
                .where(OrderLineItem.order_id == payment.order_id)
            )
            for line_item, class_ in line_items_result.all():
                order_items.append({
                    "description": line_item.description,
                    "quantity": line_item.quantity,
                    "unit_price": float(line_item.unit_price),
                    "total_price": float(line_item.total_price),
                    "class_name": class_.name if class_ else None,
                    "enrollment_id": line_item.enrollment_id,
                })

        items.append(RefundItemResponse(
            payment_id=payment.id,
            order_id=payment.order_id,
            user_id=payment.user_id,
            user_email=payment.user.email,
            user_name=payment.user.full_name,
            original_amount=float(payment.amount),
            refund_amount=float(payment.refund_amount),
            payment_status=payment.status.value,
            payment_type=payment.payment_type.value,
            refunded_at=payment.updated_at,  # Using updated_at as refund timestamp
            created_at=payment.created_at,
            order_items=order_items,
        ))

    return RefundSearchResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        total_refunded=total_refunded,
    )


@router.get("/refunds/pending", response_model=PendingRefundsListResponse)
async def list_pending_refunds(
    db_session: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> PendingRefundsListResponse:
    """Get all pending refund requests awaiting admin approval.

    Returns:
    - List of payments with pending refund requests
    - User and order details for each refund
    """
    logger.info(f"Listing pending refunds by admin: {current_admin.id}")

    from sqlalchemy.orm import joinedload

    # Get pending refunds with user and order details
    result = await db_session.execute(
        select(Payment)
        .options(
            joinedload(Payment.user),
            joinedload(Payment.order)
        )
        .where(Payment.refund_status == RefundStatus.PENDING)
        .order_by(Payment.refund_requested_at.desc())
    )
    pending_payments = result.scalars().all()

    # Format response
    items = []
    for payment in pending_payments:
        # Get brief order details
        order_details = None
        if payment.order:
            from app.models.order import OrderLineItem
            line_items_result = await db_session.execute(
                select(OrderLineItem)
                .where(OrderLineItem.order_id == payment.order_id)
                .limit(3)
            )
            line_items = line_items_result.scalars().all()
            order_details = "; ".join(
                [f"{item.description} (${item.total_price})" for item in line_items]
            )

        items.append(PendingRefundResponse(
            payment_id=payment.id,
            order_id=payment.order_id,
            user_id=payment.user_id,
            user_email=payment.user.email,
            user_name=payment.user.full_name,
            original_amount=float(payment.amount),
            refund_amount=float(payment.refund_amount),
            refund_requested_at=payment.refund_requested_at,
            payment_type=payment.payment_type.value,
            order_details=order_details,
        ))

    return PendingRefundsListResponse(
        items=items,
        total=len(items),
    )


@router.post("/refunds/{payment_id}/approve")
async def approve_refund(
    payment_id: str,
    db_session: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> dict:
    """Approve a pending refund request.

    This will:
    - Mark the refund as approved
    - Update payment status to REFUNDED or PARTIALLY_REFUNDED
    - Trigger actual refund processing (Stripe integration)
    - Send email notification to user
    """
    logger.info(f"Approving refund for payment {payment_id} by admin: {current_admin.id}")

    payment = await Payment.get_by_id(db_session, payment_id)
    if not payment:
        raise NotFoundException(f"Payment {payment_id} not found")

    if payment.refund_status != RefundStatus.PENDING:
        from core.exceptions.base import BadRequestException
        raise BadRequestException(
            message=f"Cannot approve refund with status: {payment.refund_status.value}"
        )

    await payment.approve_refund(db_session, current_admin.id)

    logger.info(
        f"Refund approved: ${payment.refund_amount} for payment {payment_id} "
        f"by {current_admin.full_name}"
    )

    # TODO: Trigger actual Stripe refund processing here
    # TODO: Send email notification to user

    return {
        "message": "Refund approved successfully",
        "payment_id": payment.id,
        "refund_amount": float(payment.refund_amount),
        "approved_by": current_admin.full_name,
    }


@router.post("/refunds/{payment_id}/reject")
async def reject_refund(
    payment_id: str,
    data: RefundApprovalRequest,
    db_session: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> dict:
    """Reject a pending refund request.

    Requires a rejection reason for user transparency.
    """
    logger.info(f"Rejecting refund for payment {payment_id} by admin: {current_admin.id}")

    payment = await Payment.get_by_id(db_session, payment_id)
    if not payment:
        raise NotFoundException(f"Payment {payment_id} not found")

    if payment.refund_status != RefundStatus.PENDING:
        from core.exceptions.base import BadRequestException
        raise BadRequestException(
            message=f"Cannot reject refund with status: {payment.refund_status.value}"
        )

    if not data.rejection_reason:
        from core.exceptions.base import BadRequestException
        raise BadRequestException(
            message="Rejection reason is required"
        )

    await payment.reject_refund(db_session, current_admin.id, data.rejection_reason)

    logger.info(
        f"Refund rejected for payment {payment_id} by {current_admin.full_name}. "
        f"Reason: {data.rejection_reason}"
    )

    # TODO: Send email notification to user with rejection reason

    return {
        "message": "Refund rejected",
        "payment_id": payment.id,
        "rejected_by": current_admin.full_name,
        "reason": data.rejection_reason,
    }


# Singleton export
__all__ = ["router"]
