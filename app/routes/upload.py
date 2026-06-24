# app/routes/upload.py
#
# POST /upload — Accepts a document file, streams it to disk, and either:
#   - Dispatches a Celery background task (default async mode)
#   - Processes synchronously and returns result (?sync=true, for small files / testing)

import os
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Query, HTTPException

from app.core.config import MAX_UPLOAD_SIZE_BYTES, ALLOWED_EXTENSIONS, UPLOAD_TEMP_DIR

logger = logging.getLogger(__name__)

router = APIRouter()

# Chunk size for streaming file to disk (1 MB)
_STREAM_CHUNK_SIZE = 1024 * 1024


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    sync: bool = Query(
        False,
        description="If true, process synchronously and return full result (for small files / testing).",
    ),
    features: Optional[str] = Query(
        None,
        description=(
            "Comma-separated list of features to run: stamp, signature, address, idproof. "
            "If omitted, all features are executed."
        ),
    ),
):
    """
    Upload a document (image or PDF) for processing.

    **Async mode (default):**
    Returns immediately with a `job_id`. Poll `GET /jobs/{job_id}` for results.

    **Sync mode (?sync=true):**
    Blocks until processing is complete and returns the full result.
    Suitable for small files or testing.

    **Feature selection (?features=stamp,address):**
    Only run the requested analysis steps. OCR and classification always run.
    """

    # ── Validate extension ────────────────────────────────────────────
    filename = file.filename or "unknown"
    extension = os.path.splitext(filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{extension}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # ── Parse features ────────────────────────────────────────────────
    from app.core.config import ALL_FEATURES, DEFAULT_FEATURES

    feature_set = DEFAULT_FEATURES
    if features:
        requested = {f.strip().lower() for f in features.split(",")}
        invalid = requested - ALL_FEATURES
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown features: {invalid}. Valid: {sorted(ALL_FEATURES)}",
            )
        feature_set = requested

    # ── Stream file to disk ───────────────────────────────────────────
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)
    temp_path = os.path.join(UPLOAD_TEMP_DIR, f"{job_id}{extension}")

    total_size = 0
    try:
        with open(temp_path, "wb") as tmp:
            while True:
                chunk = await file.read(_STREAM_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)

                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    # Clean up partial file
                    tmp.close()
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                    max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum upload size of {max_mb} MB.",
                    )

                tmp.write(chunk)

        if total_size == 0:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    except HTTPException:
        raise  # Re-raise our own exceptions
    except Exception as e:
        # Cleanup on unexpected errors
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    logger.info(
        f"File saved: {filename} ({total_size / 1024:.1f} KB) → {temp_path}"
    )

    # ── Sync mode: process immediately ────────────────────────────────
    if sync:
        return _process_sync(temp_path, filename, doc_id, feature_set)

    # ── Async mode: create job and dispatch to Celery ─────────────────
    return _dispatch_async(
        job_id=job_id,
        doc_id=doc_id,
        filename=filename,
        temp_path=temp_path,
        feature_set=feature_set,
    )


def _process_sync(
    temp_path: str, filename: str, doc_id: str, feature_set: set
) -> dict:
    """Process document synchronously (blocking). Used for ?sync=true."""
    from app.services.document_processor import DocumentProcessor

    try:
        processor = DocumentProcessor(use_minio=True)
        result = processor.process_document(
            temp_path,
            doc_id=doc_id,
            save_minio=True,
            filename=filename,
            features=feature_set,
        )
        if result["status"] == "completed":
            result["status"] = "uploaded and processed"
        return result
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _dispatch_async(
    job_id: str,
    doc_id: str,
    filename: str,
    temp_path: str,
    feature_set: set,
) -> dict:
    """Create a job record in PostgreSQL and dispatch Celery task."""
    from app.database.session import get_db_session
    from app.database.models import Job
    from app.workers.document_tasks import process_document_task

    features_list = sorted(feature_set)

    # Create job record in PostgreSQL
    session = get_db_session()
    try:
        job = Job(
            id=job_id,
            doc_id=doc_id,
            filename=filename,
            status="queued",
            step=None,
            features=features_list,
        )
        session.add(job)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create job record: {e}")
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail="Failed to create processing job.")
    finally:
        session.close()

    # Dispatch Celery task
    process_document_task.delay(
        job_id=job_id,
        file_path=temp_path,
        filename=filename,
        doc_id=doc_id,
        features=features_list,
        use_minio=True,
    )

    logger.info(f"Job {job_id} queued for async processing")

    return {
        "job_id": job_id,
        "doc_id": doc_id,
        "filename": filename,
        "status": "queued",
        "features": features_list,
        "poll_url": f"/jobs/{job_id}",
    }
