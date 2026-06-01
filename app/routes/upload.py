from fastapi import APIRouter, UploadFile, File
from app.services.document_processor import DocumentProcessor

router = APIRouter()

# ── Initialize processor with MinIO support ──
processor = DocumentProcessor(use_minio=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload document and run complete processing pipeline.

    Returns full processing result including OCR and classification.
    Intermediate results (original, preprocessed) saved to MinIO.

    Uses DocumentProcessor service to maintain code reuse with CLI scripts.
    """
    file_data = await file.read()

    result = processor.process_from_bytes(
        file_bytes=file_data,
        filename=file.filename,
        save_minio=True,
    )

    # Convert status for API compatibility
    if result["status"] == "completed":
        result["status"] = "uploaded and processed"

    return result
