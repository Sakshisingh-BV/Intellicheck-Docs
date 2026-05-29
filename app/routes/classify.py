# app/routes/classify.py
#
# Standalone /classify endpoint — accepts raw text, returns classification.
# Useful for testing rules without uploading images.

from fastapi import APIRouter
from app.classification.classifier import DocumentClassifier
from app.schemas.classify import ClassifyRequest, ClassifyResponse, ClassificationSchema

router = APIRouter()

# Reuse a single classifier instance across requests
_classifier = DocumentClassifier()


@router.post("/classify", response_model=ClassifyResponse)
async def classify_text(request: ClassifyRequest):
    """
    Classify a document from raw OCR text.

    Accepts a text string and returns the predicted document type,
    confidence score, matched keywords, and extracted fields.

    Useful for:
    - Testing classification rules without uploading images
    - Classifying text from external OCR sources
    - Debugging rule accuracy
    """

    result = _classifier.classify(request.text)

    return ClassifyResponse(
        classification=ClassificationSchema(
            document_type=result.document_type,
            display_name=result.display_name,
            confidence=round(result.confidence, 4),
            matched_keywords=result.matched_keywords,
            extracted_fields=result.extracted_fields,
            all_scores={
                k: round(v, 4) for k, v in result.all_scores.items()
            },
        ),
        raw_text_length=len(request.text),
        status="classified",
    )
