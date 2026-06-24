# app/schemas/jobs.py
#
# Pydantic schemas for the /jobs endpoint.

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class JobStatusResponse(BaseModel):
    """Response for GET /jobs/{job_id}."""

    job_id: str = Field(description="Unique job identifier (UUID)")
    doc_id: str = Field(description="Document identifier (UUID)")
    filename: str = Field(description="Original uploaded filename")
    status: str = Field(
        description="Job status: queued | processing | completed | failed"
    )
    step: Optional[str] = Field(
        None,
        description="Current processing stage (e.g. OCR, STAMP_DETECTION)",
    )
    features: Optional[List[str]] = Field(
        None, description="Requested features"
    )
    result: Optional[dict] = Field(
        None, description="Processing result (only when status=completed)"
    )
    error: Optional[str] = Field(
        None, description="Error message (only when status=failed)"
    )
    created_at: Optional[str] = Field(None, description="Job creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    completed_at: Optional[str] = Field(
        None, description="Completion timestamp"
    )


class JobListResponse(BaseModel):
    """Response for GET /jobs (list endpoint)."""

    total: int
    jobs: List[JobStatusResponse]
