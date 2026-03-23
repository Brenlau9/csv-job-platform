from celery.exceptions import CeleryError
from fastapi import APIRouter, Depends, HTTPException, status
from kombu.exceptions import OperationalError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.file import File
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse
from app.tasks.job_tasks import process_job

router = APIRouter(prefix="/jobs", tags=["jobs"])
SUPPORTED_JOB_TYPES = {"summarize"}
INITIAL_JOB_STATUS = "QUEUED"


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Job:
    if payload.job_type not in SUPPORTED_JOB_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported job type",
        )

    db_file = db.query(File).filter(File.id == payload.file_id).first()
    if db_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    if db_file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    job = Job(
        user_id=current_user.id,
        file_id=db_file.id,
        job_type=payload.job_type,
        status=INITIAL_JOB_STATUS,
        attempt_count=0,
        error_message=None,
        started_at=None,
        completed_at=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        process_job.delay(job.id)
    except (CeleryError, OperationalError, OSError) as exc:
        job.status = "FAILED"
        job.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to enqueue job",
        ) from exc

    return job
