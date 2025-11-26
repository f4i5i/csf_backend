"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from core.config import config

# Create Celery app
celery_app = Celery(
    "csf_backend",
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks from app.tasks module
celery_app.autodiscover_tasks(["app.tasks"])

# Configure periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Check for upcoming installment payments (daily at 9 AM UTC)
    "check-upcoming-installments": {
        "task": "app.tasks.email_tasks.send_upcoming_installment_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    # Check for failed payments (daily at 10 AM UTC)
    "retry-failed-payments": {
        "task": "app.tasks.payment_tasks.retry_failed_payments",
        "schedule": crontab(hour=10, minute=0),
    },
    # Process overdue installments (daily at 11 AM UTC)
    "process-overdue-installments": {
        "task": "app.tasks.payment_tasks.process_overdue_installments",
        "schedule": crontab(hour=11, minute=0),
    },
}


if __name__ == "__main__":
    celery_app.start()
