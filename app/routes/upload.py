from fastapi import APIRouter, UploadFile, File
from app.services.minio_client import client, bucket_name
from app.pipelines.ocr_pipeline import OCRPipeline
import io
import os
import json
import uuid
import tempfile
import traceback

router = APIRouter()

# ── Initialize OCR engine once (model stays in memory across requests) ──
ocr_pipeline = OCRPipeline()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    file_data = await file.read()
    doc_id = str(uuid.uuid4())

    # ── Step 1: Save original image → MinIO ──
    original_key = f"{doc_id}/original/{file.filename}"
    client.put_object(
        bucket_name,
        original_key,
        data=io.BytesIO(file_data),
        length=len(file_data),
        content_type=file.content_type,
    )

    # ── Step 2: Temp file for PaddleOCR to read ──
    suffix = os.path.splitext(file.filename)[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(file_data)
        tmp.close()

        # ── Step 3: Run OCR directly on raw image ──
        # PaddleOCR 3.5 handles orientation, unwarping, enhancement internally.
        # No need for custom preprocessing — it slows things down and can
        # degrade neural OCR accuracy.
        parsed_result, formatted_result, quality_info = ocr_pipeline.run(
            tmp.name,
            check_quality=True,
        )

        # ── Step 4: Save OCR JSON → MinIO ──
        base_name = os.path.splitext(file.filename)[0]
        ocr_json_bytes = json.dumps(
            formatted_result, indent=4, ensure_ascii=False
        ).encode("utf-8")

        ocr_key = f"{doc_id}/ocr/{base_name}_ocr_result.json"
        client.put_object(
            bucket_name,
            ocr_key,
            data=io.BytesIO(ocr_json_bytes),
            length=len(ocr_json_bytes),
            content_type="application/json",
        )

    except Exception as e:
        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "original_key": original_key,
            "status": "processing_failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
    finally:
        os.unlink(tmp.name)

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "original_key": original_key,
        "ocr_key": ocr_key,
        "quality": quality_info,
        "ocr_result": formatted_result,
        "status": "uploaded and OCR complete",
    }