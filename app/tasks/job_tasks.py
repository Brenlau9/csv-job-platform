from datetime import UTC, datetime

from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.models.job import Job
from app.models.job_result import JobResult
from app.processors.summarize import summarize_csv
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.process_job")
def process_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = (
            db.query(Job)
            .options(joinedload(Job.file), joinedload(Job.result))
            .filter(Job.id == job_id)
            .first()
        )
        if job is None:
            return

        job.status = "PROCESSING"
        job.started_at = datetime.now(UTC)
        job.completed_at = None
        job.error_message = None
        job.attempt_count += 1
        db.commit()
        db.refresh(job)

        if job.job_type != "summarize":
            raise ValueError(f"Unsupported job type: {job.job_type}")

        if job.file is None:
            raise ValueError("Associated file not found")

        summary = summarize_csv(job.file.stored_path)
        if job.result is None:
            db.add(JobResult(job_id=job.id, result_json=summary))
        else:
            job.result.result_json = summary

        job.status = "COMPLETED"
        job.completed_at = datetime.now(UTC)
        job.error_message = None
        db.commit()
    except Exception as exc:
        db.rollback()
        failed_job = db.query(Job).filter(Job.id == job_id).first()
        if failed_job is not None:
            failed_job.status = "FAILED"
            failed_job.error_message = str(exc)
            failed_job.completed_at = datetime.now(UTC)
            if failed_job.started_at is None:
                failed_job.started_at = datetime.now(UTC)
            db.commit()
        raise
    finally:
        db.close()
