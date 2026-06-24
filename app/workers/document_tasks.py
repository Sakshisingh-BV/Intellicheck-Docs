"""
Celery background task for document processing.

Runs the full document pipeline (preprocessing → OCR → classification →
stamp detection → address/idproof) in a worker process with progress
reporting to both Redis (Celery state) and PostgreSQL (permanent audit).
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# ── Lazy-loaded processor (expensive: loads PaddleOCR + YOLO) ────────────

_processor = None


def _get_processor(use_minio: bool = False):
    """Lazy-init the DocumentProcessor so model loading happens once per worker."""
    global _processor
    if _processor is None:
        from app.services.document_processor import DocumentProcessor

        _processor = DocumentProcessor(use_minio=use_minio)
        logger.info("DocumentProcessor initialized in worker")
    return _processor


# ── PostgreSQL job status updates ────────────────────────────────────────

def _update_job(
    job_id: str,
    status: str,
    step: Optional[str] = None,
    result: Optional[dict] = None,
    error: Optional[str] = None,
):
    """Update job record in PostgreSQL."""
    from app.database.session import get_db_session
    from app.database.models import Job

    session = get_db_session()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return

        job.status = status
        if step is not None:
            job.step = step
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        if status in ("completed", "failed"):
            job.completed_at = datetime.now(timezone.utc)

        session.commit()
        logger.debug(f"Job {job_id}: status={status}, step={step}")

    except Exception as exc:
        session.rollback()
        logger.error(f"Failed to update job {job_id}: {exc}")
    finally:
        session.close()


# ── Celery task ──────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="process_document",
    max_retries=1,
    acks_late=True,
)
def process_document_task(
    self,
    job_id: str,
    file_path: str,
    filename: str,
    doc_id: str,
    features: list,
    use_minio: bool = False,
):
    """
    Background document processing task.

    Args:
        job_id:     UUID identifying the job row in PostgreSQL.
        file_path:  Path to the uploaded temp file on disk.
        filename:   Original filename from the client.
        doc_id:     Document UUID for MinIO storage paths.
        features:   List of requested features (stamp, signature, address, idproof).
        use_minio:  Whether to save intermediates to MinIO.
    """
    try:
        # ── INITIALIZING ─────────────────────────────────────────────
        _update_job(job_id, "processing", step="INITIALIZING")
        self.update_state(state="PROCESSING", meta={"step": "INITIALIZING"})

        processor = _get_processor(use_minio)

        # Build a progress callback that updates both Redis and PostgreSQL
        def progress_callback(step: str):
            _update_job(job_id, "processing", step=step)
            self.update_state(state="PROCESSING", meta={"step": step})

        # ── RUN PIPELINE ─────────────────────────────────────────────
        feature_set = set(features) if features else None

        result = processor.process_document(
            file_path,
            doc_id=doc_id,
            save_minio=use_minio,
            filename=filename,
            features=feature_set,
            progress_callback=progress_callback,
        )

        # ── FINALIZING ───────────────────────────────────────────────
        progress_callback("FINALIZING")
        _update_job(job_id, "completed", step="FINALIZING", result=result)

        logger.info(f"Job {job_id} completed successfully")
        return {"job_id": job_id, "status": "completed"}

    except Exception as exc:
        logger.error(f"Job {job_id} failed: {exc}", exc_info=True)
        _update_job(job_id, "failed", error=str(exc))
        # Don't re-raise — we want the job to be marked as failed,
        # not retried endlessly.
        return {"job_id": job_id, "status": "failed", "error": str(exc)}

    finally:
        # ── CLEANUP TEMP FILE (robust try/finally) ───────────────────
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as cleanup_err:
            logger.warning(
                f"Failed to cleanup temp file {file_path}: {cleanup_err}"
            )
