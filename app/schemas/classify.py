# app/schemas/classify.py

from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    """Request body for the /classify endpoint."""

    text: str = Field(
        ...,
        min_length=1,
        description="Raw OCR text to classify.",
        examples=["GOVERNMENT OF INDIA AADHAAR Unique Identification Authority"],
    )


class ClassificationSchema(BaseModel):
    """Classification result embedded in responses."""

    document_type: str = Field(
        description="Canonical document type, e.g. 'aadhaar_card'."
    )
    display_name: str = Field(
        description="Human-readable document name."
    )
    confidence: float = Field(
        description="Classification confidence from 0.0 to 1.0."
    )
    matched_keywords: list = Field(
        description="Keywords from the rules that matched."
    )
    extracted_fields: dict = Field(
        description="Structured fields extracted via regex."
    )
    all_scores: dict = Field(
        default_factory=dict,
        description="Scores for all document types (debugging)."
    )


class ClassifyResponse(BaseModel):
    """Response body for the /classify endpoint."""

    classification: ClassificationSchema
    raw_text_length: int = Field(
        description="Length of the input text."
    )
    status: str = "classified"
