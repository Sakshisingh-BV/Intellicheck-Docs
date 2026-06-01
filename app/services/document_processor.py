"""
Document processing service layer.

Shared by both FastAPI routes and CLI scripts.
Orchestrates preprocessing → OCR → classification flow.
MinIO integration is optional.
"""

import os
import io
import cv2
import uuid
import tempfile
import logging
from typing import Dict, Any, Optional, Tuple

from app.preprocessing.utils import load_image
from app.preprocessing.blur import detect_blur, sharpen_image
from app.pipelines.ocr_pipeline import OCRPipeline
from app.pipelines.classification_pipeline import ClassificationPipeline

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Unified document processing pipeline.
    
    Handles preprocessing, OCR, and classification.
    Can optionally integrate with MinIO.
    """

    def __init__(self, use_minio: bool = False):
        """
        Initialize processor.
        
        Args:
            use_minio: If True, save intermediate results to MinIO.
                      MinIO client must be configured in app.services.minio_client.
        """
        self.ocr_pipeline = OCRPipeline()
        self.classification_pipeline = ClassificationPipeline()
        self.use_minio = use_minio
        self.minio_client = None
        self.bucket_name = None

        if use_minio:
            try:
                from app.services.minio_client import client, bucket_name
                self.minio_client = client
                self.bucket_name = bucket_name
                logger.info("MinIO integration enabled")
            except Exception as e:
                logger.warning(f"MinIO integration failed: {e}. Continuing without MinIO.")
                self.use_minio = False

    def process_document(
        self,
        image_path: str,
        doc_id: Optional[str] = None,
        save_minio: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a document from image file to final results.

        Pipeline:
            1. Load image
            2. Preprocessing (quality check, sharpening)
            3. OCR (parse + format)
            4. Classification

        Args:
            image_path: Path to input image file.
            doc_id: Optional document ID (generated if not provided).
            save_minio: If True and MinIO configured, save intermediate results.
            **kwargs: Additional metadata to include in response.

        Returns:
            Dict with keys:
                - doc_id
                - filename
                - quality (blur_score, is_blurry, blur_level)
                - ocr_result (formatted OCR output)
                - classification (document type, confidence, etc.)
                - preprocessing (saved object keys if saved to MinIO)
                - status
                - error (if processing failed)
                - traceback (if processing failed)
        """
        doc_id = doc_id or str(uuid.uuid4())
        filename = os.path.basename(image_path)

        result = {
            "doc_id": doc_id,
            "filename": filename,
            "status": "processing",
            "classification": None,  # Initialize classification field
        }

        # Merge any additional metadata
        result.update(kwargs)

        try:
            # ── Step 1: Preprocessing ──
            logger.info(f"Processing {filename} (doc_id={doc_id})")

            image = load_image(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Quality check
            blur_result = detect_blur(gray)
            quality_info = {
                "blur_score": blur_result["blur_score"],
                "is_blurry": blur_result["is_blurry"],
                "blur_level": blur_result["blur_level"],
            }

            # Sharpen if blurry
            preprocessed = sharpen_image(gray) if blur_result["is_blurry"] else gray

            result["quality"] = quality_info

            # ── Step 2: Optionally save preprocessed image to MinIO ──
            preprocessing_info = {}
            if save_minio and self.use_minio and self.minio_client:
                try:
                    _, img_encoded = cv2.imencode(".png", preprocessed)
                    preprocessed_bytes = img_encoded.tobytes()

                    base_name = os.path.splitext(filename)[0]
                    original_key = f"{doc_id}/original/{filename}"
                    preprocessed_key = f"{doc_id}/preprocessed/{base_name}_preprocessed.png"

                    # Save original
                    with open(image_path, 'rb') as f:
                        original_data = f.read()
                    self.minio_client.put_object(
                        self.bucket_name,
                        original_key,
                        data=io.BytesIO(original_data),
                        length=len(original_data),
                        content_type="image/png",
                    )

                    # Save preprocessed
                    self.minio_client.put_object(
                        self.bucket_name,
                        preprocessed_key,
                        data=io.BytesIO(preprocessed_bytes),
                        length=len(preprocessed_bytes),
                        content_type="image/png",
                    )

                    preprocessing_info["original_key"] = original_key
                    preprocessing_info["preprocessed_key"] = preprocessed_key
                    logger.info(f"Saved to MinIO: {original_key}, {preprocessed_key}")

                except Exception as e:
                    logger.warning(f"Failed to save to MinIO: {e}")

            if preprocessing_info:
                result["preprocessing"] = preprocessing_info

            # ── Step 3: Run OCR ──
            logger.info(f"Running OCR for {doc_id}")
            parsed_result, formatted_result, _ = self.ocr_pipeline.run(
                image_path,
                check_quality=False,  # Already checked above
            )

            result["ocr_result"] = formatted_result

            # ── Step 4: Classify ──
            logger.info(f"Classifying document {doc_id}")
            classification_result = self.classification_pipeline.run(parsed_result)
            result["classification"] = classification_result.to_dict()

            result["status"] = "completed"

        except Exception as e:
            logger.error(f"Error processing {doc_id}: {e}", exc_info=True)
            result["status"] = "processing_failed"
            result["error"] = str(e)
            result["classification"] = result["classification"] or {
                "document_type": "unknown",
                "display_name": "Unknown Document",
                "confidence": 0.0,
                "matched_keywords": [],
                "extracted_fields": {},
                "all_scores": {}
            }
            import traceback
            result["traceback"] = traceback.format_exc()

        return result

    def process_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        doc_id: Optional[str] = None,
        save_minio: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a document from bytes (e.g., uploaded file).

        Writes bytes to temp file, processes, then cleans up.

        Args:
            file_bytes: Raw image bytes.
            filename: Original filename.
            doc_id: Optional document ID.
            save_minio: If True, save to MinIO.
            **kwargs: Additional metadata.

        Returns:
            Processing result dict.
        """
        doc_id = doc_id or str(uuid.uuid4())
        suffix = os.path.splitext(filename)[1] or ".png"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

        try:
            tmp.write(file_bytes)
            tmp.close()
            return self.process_document(
                tmp.name,
                doc_id=doc_id,
                save_minio=save_minio,
                filename=filename,
                **kwargs
            )
        finally:
            try:
                os.unlink(tmp.name)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp.name}: {e}")
