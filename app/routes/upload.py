from fastapi import APIRouter, UploadFile, File
from app.services.minio_client import client, bucket_name
from app.pipelines.ocr_pipeline import OCRPipeline
from app.pipelines.classification_pipeline import ClassificationPipeline
from app.preprocessing.utils import load_image
from app.preprocessing.blur import detect_blur, sharpen_image
import cv2
import io
import os
import numpy as np
import uuid
import tempfile
import traceback

router = APIRouter()

# ── Initialize pipelines once (stay in memory across requests) ──
ocr_pipeline = OCRPipeline()
classification_pipeline = ClassificationPipeline()


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

    # ── Step 2: Temp file for processing ──
    suffix = os.path.splitext(file.filename)[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(file_data)
        tmp.close()

        # ── Step 3: Create preprocessed image & save → MinIO ──
        image = load_image(tmp.name)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Quality check on the grayscale image
        blur_result = detect_blur(gray)
        quality_info = {
            "blur_score": blur_result["blur_score"],
            "is_blurry": blur_result["is_blurry"],
            "blur_level": blur_result["blur_level"],
        }

        # Sharpen if the image is blurry
        preprocessed = sharpen_image(gray) if blur_result["is_blurry"] else gray

        # Encode preprocessed image to PNG bytes
        _, img_encoded = cv2.imencode(".png", preprocessed)
        preprocessed_bytes = img_encoded.tobytes()

        base_name = os.path.splitext(file.filename)[0]
        preprocessed_key = f"{doc_id}/preprocessed/{base_name}_preprocessed.png"
        client.put_object(
            bucket_name,
            preprocessed_key,
            data=io.BytesIO(preprocessed_bytes),
            length=len(preprocessed_bytes),
            content_type="image/png",
        )

        # ── Step 4: Run OCR (result returned in response only, not saved to MinIO) ──
        parsed_result, formatted_result, _ = ocr_pipeline.run(
            tmp.name,
            check_quality=False,  # already checked above
        )

        # ── Step 5: Classify document type from OCR text ──
        classification_result = classification_pipeline.run(parsed_result)

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
        "preprocessed_key": preprocessed_key,
        "quality": quality_info,
        "classification": classification_result.to_dict(),
        "ocr_result": formatted_result,
        "status": "uploaded and processed",
    }
