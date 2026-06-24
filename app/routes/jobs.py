# app/routes/jobs.py
#
# GET /jobs/{job_id} — Poll processing job status
# GET /jobs          — List recent jobs

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Poll the status of a document processing job.

    Returns:
        - `queued`     — Waiting in the Celery queue.
        - `processing` — Actively being processed. `step` shows current stage.
        - `completed`  — Done. `result` contains the full processing output.
        - `failed`     — Processing failed. `error` contains details.

    Progress stages (in order):
        INITIALIZING → PREPROCESSING → OCR → STAMP_DETECTION →
        SIGNATURE_DETECTION → ADDRESS_CHECK → ID_PROOF_CHECK → FINALIZING
    """
    from app.database.session import get_db_session
    from app.database.models import Job

    session = get_db_session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        return job.to_dict()
    finally:
        session.close()


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(
        None,
        description="Filter by status: queued, processing, completed, failed",
    ),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List recent processing jobs, optionally filtered by status.
    Ordered by creation time (newest first).
    """
    from app.database.session import get_db_session
    from app.database.models import Job

    session = get_db_session()
    try:
        query = session.query(Job).order_by(Job.created_at.desc())

        if status:
            valid_statuses = {"queued", "processing", "completed", "failed"}
            if status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status '{status}'. Valid: {sorted(valid_statuses)}",
                )
            query = query.filter(Job.status == status)

        total = query.count()
        jobs = query.offset(offset).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "jobs": [job.to_dict() for job in jobs],
        }
    finally:
        session.close()
