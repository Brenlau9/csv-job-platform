"""Task package."""
from app.tasks.celery_app import celery_app
from app.tasks.job_tasks import process_job

__all__ = ["celery_app", "process_job"]
