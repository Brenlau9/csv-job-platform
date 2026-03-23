from celery.exceptions import CeleryError
from fastapi import APIRouter, Depends, HTTPException, status
from kombu.exceptions import OperationalError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.file import File
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobCreate, JobResponse, JobResultResponse, JobStatusResponse, SummaryResultPayload
from app.tasks.job_tasks import process_job

router = APIRouter(prefix="/jobs", tags=["jobs"])
SUPPORTED_JOB_TYPES = {"summarize"}
INITIAL_JOB_STATUS = "QUEUED"


def _get_owned_job(db: Session, job_id: int, user_id: int) -> Job:
    job = (
        db.query(Job)
        .options(joinedload(Job.result))
        .filter(Job.id == job_id, Job.user_id == user_id)
        .first()
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job


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


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobStatusResponse:
    job = _get_owned_job(db, job_id=job_id, user_id=current_user.id)
    return JobStatusResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/{job_id}/result", response_model=JobResultResponse)
def get_job_result(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResultResponse:
    job = _get_owned_job(db, job_id=job_id, user_id=current_user.id)
    if job.result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job result not found",
        )

    result_json = job.result.result_json
    columns = result_json.get("columns", result_json.get("column_names", []))
    payload = SummaryResultPayload(
        row_count=result_json.get("row_count", 0),
        column_count=result_json.get("column_count", len(columns)),
        columns=columns,
        null_counts=result_json.get("null_counts", {}),
    )
    return JobResultResponse(job_id=job.id, result=payload)
