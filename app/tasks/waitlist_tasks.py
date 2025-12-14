"""Background tasks for waitlist management."""

from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child
from app.models.class_ import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.user import User
from app.tasks.email_tasks import send_email
from core.db import async_session_maker
from core.logging import get_logger

logger = get_logger(__name__)


@shared_task(name="process_expired_claim_windows")
def process_expired_claim_windows():
    """
    Process expired waitlist claim windows.

    Runs periodically (e.g., every 15 minutes) to:
    1. Expire unclaimed regular waitlist spots
    2. Notify next person in line
    """
    import asyncio

    asyncio.run(_process_expired_claim_windows_async())


async def _process_expired_claim_windows_async():
    """Async implementation of claim window processing."""
    async with async_session_maker() as db_session:
        logger.info("Processing expired waitlist claim windows")

        # Get all expired claim windows
        expired_enrollments = await Enrollment.get_expired_claim_windows(db_session)

        if not expired_enrollments:
            logger.info("No expired claim windows found")
            return

        logger.info(f"Found {len(expired_enrollments)} expired claim windows")

        for enrollment in expired_enrollments:
            try:
                # Expire the claim window
                await enrollment.expire_claim_window(db_session)

                # Get user and child info for notification
                user = await db_session.get(User, enrollment.user_id)
                child = await db_session.get(Child, enrollment.child_id)
                class_ = await db_session.get(Class, enrollment.class_id)

                if user and child and class_:
                    # Send expiration notification
                    send_waitlist_expired_email.delay(
                        user_email=user.email,
                        user_name=user.full_name,
                        child_name=child.full_name,
                        class_name=class_.name,
                    )

                # Check if there's a next person in line
                next_enrollment = await Enrollment.get_next_in_waitlist(
                    db_session, enrollment.class_id
                )

                if next_enrollment:
                    # Start claim window for next regular waitlist entry
                    # or auto-promote priority waitlist
                    if next_enrollment.auto_promote:
                        # TODO: Auto-charge and promote
                        logger.info(
                            f"Auto-promoting priority waitlist enrollment {next_enrollment.id}"
                        )
                        # await next_enrollment.promote_from_waitlist(db_session, auto_charged=True)
                        # Update class count...
                    else:
                        # Start 12-hour claim window for regular waitlist
                        await next_enrollment.start_claim_window(db_session)

                        # Notify user
                        next_user = await db_session.get(User, next_enrollment.user_id)
                        next_child = await db_session.get(Child, next_enrollment.child_id)
                        next_class = await db_session.get(Class, next_enrollment.class_id)

                        if next_user and next_child and next_class:
                            send_waitlist_spot_available_email.delay(
                                user_email=next_user.email,
                                user_name=next_user.full_name,
                                child_name=next_child.full_name,
                                class_name=next_class.name,
                                claim_window_expires_at=next_enrollment.claim_window_expires_at.isoformat(),
                            )

                logger.info(f"Processed expired claim window for enrollment {enrollment.id}")

            except Exception as e:
                logger.error(
                    f"Error processing expired claim window for enrollment {enrollment.id}: {e}",
                    exc_info=True,
                )
                continue


@shared_task(name="send_waitlist_spot_available_email")
def send_waitlist_spot_available_email(
    user_email: str,
    user_name: str,
    child_name: str,
    class_name: str,
    claim_window_expires_at: str,
):
    """Send email notification when a waitlist spot becomes available."""
    subject = f"Spot Available for {child_name} - {class_name}"

    body = f"""
    <h2>Great News! A Spot is Available</h2>
    <p>Hello {user_name},</p>

    <p>A spot has opened up in <strong>{class_name}</strong> for {child_name}!</p>

    <p><strong>You have 12 hours to claim this spot.</strong></p>

    <p>Your claim window expires at: <strong>{claim_window_expires_at}</strong></p>

    <p>To claim your spot, please log in to your account and complete the payment.</p>

    <p>If you don't claim the spot within 12 hours, it will be offered to the next person on the waitlist.</p>

    <p>Best regards,<br>The CSF Team</p>
    """

    send_email.delay(
        to_email=user_email,
        subject=subject,
        html_content=body,
    )


@shared_task(name="send_waitlist_expired_email")
def send_waitlist_expired_email(
    user_email: str,
    user_name: str,
    child_name: str,
    class_name: str,
):
    """Send email notification when a waitlist claim window expires."""
    subject = f"Waitlist Spot Expired - {class_name}"

    body = f"""
    <h2>Waitlist Spot Expired</h2>
    <p>Hello {user_name},</p>

    <p>Unfortunately, the waitlist spot for {child_name} in <strong>{class_name}</strong> has expired.</p>

    <p>The 12-hour claim window has passed without payment, so the spot has been offered to the next person on the waitlist.</p>

    <p>If you're still interested in this class, you can rejoin the waitlist.</p>

    <p>Best regards,<br>The CSF Team</p>
    """

    send_email.delay(
        to_email=user_email,
        subject=subject,
        html_content=body,
    )


@shared_task(name="notify_waitlist_position")
def notify_waitlist_position(
    user_email: str,
    user_name: str,
    child_name: str,
    class_name: str,
    position: int,
):
    """Notify user of their position on the waitlist."""
    subject = f"Waitlist Confirmation - {class_name}"

    priority_text = "priority (auto-charge)" if position <= 5 else "regular"

    body = f"""
    <h2>Waitlist Confirmation</h2>
    <p>Hello {user_name},</p>

    <p>You've been added to the waitlist for <strong>{class_name}</strong> for {child_name}.</p>

    <p>Your current position: <strong>#{position}</strong></p>

    <p>We'll notify you as soon as a spot becomes available.</p>

    <p>Best regards,<br>The CSF Team</p>
    """

    send_email.delay(
        to_email=user_email,
        subject=subject,
        html_content=body,
    )
