# app/schemas/upload.py

from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.classify import ClassificationSchema


class QualitySchema(BaseModel):
    """Image quality assessment results."""

    blur_score: float
    is_blurry: bool
    blur_level: str


class UploadResponseSchema(BaseModel):
    """Full response for the /upload endpoint."""

    doc_id: str
    filename: str
    original_key: str
    preprocessed_key: str
    quality: QualitySchema
    classification: ClassificationSchema
    ocr_result: dict
    status: str = "uploaded and processed"
