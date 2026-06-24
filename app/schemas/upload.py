# app/schemas/upload.py

from pydantic import BaseModel, Field
from typing import Optional, List
from app.schemas.classify import ClassificationSchema


class QualitySchema(BaseModel):
    """Image quality assessment results."""

    blur_score: float
    is_blurry: bool
    blur_level: str


class UploadResponseSchema(BaseModel):
    """Full response for the /upload endpoint (sync mode)."""

    doc_id: str
    filename: str
    original_key: str
    preprocessed_key: str
    quality: QualitySchema
    classification: ClassificationSchema
    ocr_result: dict
    status: str = "uploaded and processed"


class UploadAcceptedSchema(BaseModel):
    """Response when file is accepted for async processing."""

    job_id: str = Field(description="Unique job identifier for polling")
    doc_id: str = Field(description="Document identifier")
    filename: str = Field(description="Original uploaded filename")
    status: str = Field(default="queued", description="Initial job status")
    features: List[str] = Field(description="Features that will be processed")
    poll_url: str = Field(description="URL to poll for job status")
