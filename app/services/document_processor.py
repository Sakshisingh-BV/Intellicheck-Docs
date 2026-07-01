"""
Document processing service layer.

Orchestrates preprocessing → OCR → classification → stamp detection flow.
Used by CLI scripts and test harnesses.
"""

import os
import cv2
import uuid
import tempfile
import logging
from typing import Dict, Any, Optional, List, Callable, Set

from app.preprocessing.utils import load_image
from app.preprocessing.blur import detect_blur, sharpen_image
from app.document_parsing import PDFParser
from app.pipelines.ocr_pipeline import OCRPipeline
from app.pipelines.classification_pipeline import ClassificationPipeline
from app.pipelines.stamp_detection_pipeline import StampDetectionPipeline
from app.address_verification.extractor import AddressExtractor
from app.validation.validators import validate_extracted_fields

logger = logging.getLogger(__name__)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PDF_EXTENSION = ".pdf"


class DocumentProcessor:
    """
    Unified document processing pipeline.
    
    Handles preprocessing, OCR, classification, stamp detection,
    address verification, and ID proof validation.
    """

    def __init__(self):
        """Initialize processor with all pipeline components."""
        self.ocr_pipeline = OCRPipeline()
        self.classification_pipeline = ClassificationPipeline()
        self.stamp_pipeline = StampDetectionPipeline(
            ocr_engine=self.ocr_pipeline.engine
        )
        self.pdf_parser = PDFParser()

    def process_document(
        self,
        image_path: str,
        doc_id: Optional[str] = None,
        output_dir: Optional[str] = None,
        features: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a document from an image or PDF file to final results.

        Pipeline:
            1. Parse input document (PDF pages become images)
            2. Preprocessing (quality check, sharpening)
            3. OCR (parse + format)
            4. Classification
            5. Stamp / signature / QR detection
            6. Address extraction
            7. ID proof field validation

        Args:
            image_path: Path to input image or PDF file.
            doc_id: Optional document ID (generated if not provided).
            output_dir: Optional directory path to save visualization images.
            features: Optional set of features to run (stamp, signature, address, idproof).
                      If None, all features are enabled.
            progress_callback: Optional callback for progress reporting.
            **kwargs: Additional metadata to include in response.

        Returns:
            Dict with keys:
                - doc_id
                - filename
                - quality (blur_score, is_blurry, blur_level)
                - ocr_result (formatted OCR output)
                - classification (document type, confidence, etc.)
                - stamp_detection (stamps, signatures, QR, bounding boxes)
                - status
                - error (if processing failed)
                - traceback (if processing failed)
        """
        doc_id = doc_id or str(uuid.uuid4())
        metadata = dict(kwargs)
        filename = metadata.pop("filename", os.path.basename(image_path))
        extension = os.path.splitext(filename)[1].lower()

        if extension == PDF_EXTENSION:
            return self._process_pdf_document(
                image_path,
                doc_id=doc_id,
                filename=filename,
                output_dir=output_dir,
                features=features,
                progress_callback=progress_callback,
                **metadata
            )

        if extension not in IMAGE_EXTENSIONS:
            return {
                "doc_id": doc_id,
                "filename": filename,
                "status": "unsupported_file_type",
                "error": f"Unsupported document type: {extension or 'unknown'}",
                "classification": self._unknown_classification(),
            }

        return self._process_image_document(
            image_path,
            doc_id=doc_id,
            filename=filename,
            output_dir=output_dir,
            features=features,
            progress_callback=progress_callback,
            **metadata
        )

    def _process_image_document(
        self,
        image_path: str,
        doc_id: str,
        filename: Optional[str] = None,
        page_number: Optional[int] = None,
        source_file: Optional[str] = None,
        output_dir: Optional[str] = None,
        features: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        filename = filename or os.path.basename(image_path)

        # When features is None, run everything (backward compatible)
        run_stamp = features is None or "stamp" in features or "signature" in features
        run_address = features is None or "address" in features
        run_idproof = features is None or "idproof" in features

        result = {
            "doc_id": doc_id,
            "filename": filename,
            "file_type": "image",
            "status": "processing",
            "classification": None,
            "stamp_detection": None,
        }

        if page_number is not None:
            result["page_number"] = page_number
        if source_file:
            result["source_file"] = source_file

        # Merge any additional metadata (excludes features/progress_callback)
        extra = {k: v for k, v in kwargs.items()
                 if k not in ("features", "progress_callback")}
        result.update(extra)

        try:
            # ── Step 1: Preprocessing ──
            if progress_callback:
                progress_callback("PREPROCESSING")
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

            # ── Step 2: Run OCR ──
            if progress_callback:
                progress_callback("OCR")
            logger.info(f"Running OCR for {doc_id}")
            parsed_result, formatted_result, _ = self.ocr_pipeline.run(
                image,
                check_quality=False,  # Already checked above
                image_name=filename,
            )

            result["ocr_result"] = formatted_result

            # ── Step 3: Classify ──
            logger.info(f"Classifying document {doc_id}")
            classification_result = self.classification_pipeline.run(parsed_result)
            result["classification"] = classification_result.to_dict()

            # ── Step 4: Stamp / Signature / QR Detection (conditional) ──
            if run_stamp:
                if progress_callback:
                    progress_callback("STAMP_DETECTION")
                logger.info(f"Running stamp detection for {doc_id}")
                stamp_result = self.stamp_pipeline.process(
                    image,
                    image_path=image_path,
                    ocr_text=formatted_result.get("text", ""),
                )
                result["stamp_detection"] = self._serialize_stamp_result(stamp_result)

                # Report signature detection as a separate progress stage
                if progress_callback:
                    progress_callback("SIGNATURE_DETECTION")

                # Save bounding box visualization if output_dir is set
                if output_dir and stamp_result.get("success"):
                    self._save_detection_visualization(
                        image, stamp_result, output_dir, filename, page_number
                    )

            # ── Step 5: Address Extraction (conditional) ──
            if run_address:
                if progress_callback:
                    progress_callback("ADDRESS_CHECK")
                result["address_extraction"] = self._run_address_extraction(
                    doc_id, formatted_result
                )

            # ── Step 6: ID Proof Field Validation (conditional) ──
            if run_idproof:
                if progress_callback:
                    progress_callback("ID_PROOF_CHECK")
                result["field_validation"] = self._run_field_validation(
                    doc_id, classification_result
                )

            result["status"] = "completed"

        except Exception as e:
            logger.error(f"Error processing {doc_id}: {e}", exc_info=True)
            result["status"] = "processing_failed"
            result["error"] = str(e)
            result["classification"] = result["classification"] or self._unknown_classification()
            result["stamp_detection"] = result["stamp_detection"] or {"success": False, "error": str(e)}
            import traceback
            result["traceback"] = traceback.format_exc()

        return result

    def _process_pdf_document(
        self,
        pdf_path: str,
        doc_id: str,
        filename: Optional[str] = None,
        output_dir: Optional[str] = None,
        features: Optional[Set[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        filename = filename or os.path.basename(pdf_path)
        result = {
            "doc_id": doc_id,
            "filename": filename,
            "file_type": "pdf",
            "status": "processing",
            "classification": None,
            "stamp_detection": None,
        }
        extra = {k: v for k, v in kwargs.items()
                 if k not in ("features", "progress_callback")}
        result.update(extra)

        page_images = []

        try:
            logger.info(f"Rendering PDF {filename} (doc_id={doc_id})")
            page_images = self.pdf_parser.parse(pdf_path)

            pages = []
            for page_image in page_images:
                page_result = self._process_image_document(
                    page_image.image_path,
                    doc_id=f"{doc_id}-page-{page_image.page_number}",
                    filename=f"{os.path.splitext(filename)[0]}_page{page_image.page_number}.png",
                    page_number=page_image.page_number,
                    source_file=filename,
                    output_dir=output_dir,
                    features=features,
                    progress_callback=progress_callback,
                )
                pages.append(page_result)

            result["page_count"] = len(pages)
            result["pages"] = pages
            result["ocr_result"] = self._merge_page_ocr(filename, pages)
            result["classification"] = self._best_page_classification(pages)
            result["stamp_detection"] = self._aggregate_stamp_detections(pages)
            result["status"] = (
                "completed"
                if pages and all(page["status"] == "completed" for page in pages)
                else "processing_failed"
            )

            failed_pages = [
                page["page_number"]
                for page in pages
                if page.get("status") != "completed"
            ]
            if failed_pages:
                result["failed_pages"] = failed_pages

        except Exception as e:
            logger.error(f"Error processing PDF {doc_id}: {e}", exc_info=True)
            result["status"] = "processing_failed"
            result["error"] = str(e)
            result["classification"] = result["classification"] or self._unknown_classification()
            result["stamp_detection"] = result["stamp_detection"] or {"success": False, "error": str(e)}
            import traceback
            result["traceback"] = traceback.format_exc()
        finally:
            for page_image in page_images:
                try:
                    os.unlink(page_image.image_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {page_image.image_path}: {e}")

        return result

    def _merge_page_ocr(self, filename: str, pages: list) -> Dict[str, Any]:
        page_ocr_results = [
            page.get("ocr_result", {})
            for page in pages
            if page.get("ocr_result")
        ]
        merged_text = "\n\n".join(
            page_ocr.get("text", "")
            for page_ocr in page_ocr_results
            if page_ocr.get("text")
        ).strip()
        merged_blocks = []

        for page in pages:
            page_number = page.get("page_number")
            for block in page.get("ocr_result", {}).get("results", []):
                block_with_page = dict(block)
                block_with_page["page_number"] = page_number
                merged_blocks.append(block_with_page)

        return {
            "document_name": filename,
            "text": merged_text,
            "total_blocks": len(merged_blocks),
            "results": merged_blocks,
            "pages": page_ocr_results,
        }

    def _best_page_classification(self, pages: list) -> Dict[str, Any]:
        classifications = [
            page.get("classification")
            for page in pages
            if page.get("classification")
        ]
        if not classifications:
            return self._unknown_classification()

        return max(
            classifications,
            key=lambda classification: classification.get("confidence", 0.0),
        )

    def _unknown_classification(self) -> Dict[str, Any]:
        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": 0.0,
            "matched_keywords": [],
            "extracted_fields": {},
            "all_scores": {}
        }

    # ------------------------------------------------------------------
    # Stamp detection helpers
    # ------------------------------------------------------------------

    def _serialize_stamp_result(self, stamp_result: Dict[str, Any]) -> Dict[str, Any]:
        """Strip non-serializable numpy arrays from stamp detection output."""
        result = dict(stamp_result)
        serializable_detections = []
        for det in result.get("raw_detections", []):
            det_copy = {k: v for k, v in det.items() if k != "crop"}
            serializable_detections.append(det_copy)
        result["raw_detections"] = serializable_detections

        # Strip crops from analysis sub-lists too
        analysis = result.get("analysis", {})
        for key in ("valid_stamps", "invalid_stamps", "signatures"):
            if key in analysis:
                analysis[key] = [
                    {k: v for k, v in d.items() if k != "crop"}
                    for d in analysis[key]
                ]

        # Convert numpy image_shape tuple to list for JSON
        if "image_shape" in result:
            try:
                result.pop("image_shape", None)
            except Exception:
                pass

        return result

    def _aggregate_stamp_detections(self, pages: list) -> Dict[str, Any]:
        """Aggregate per-page stamp detection results into a document-level summary."""
        all_stamps = []
        all_signatures = []
        all_qr_codes = []
        is_estamp = False
        best_estamp_score = 0
        document_fields = {}

        for page in pages:
            sd = page.get("stamp_detection")
            if not sd or not sd.get("success"):
                continue

            page_number = page.get("page_number")
            bboxes = sd.get("bounding_boxes", {})

            for s in bboxes.get("stamps", []):
                s_copy = dict(s)
                s_copy["page_number"] = page_number
                all_stamps.append(s_copy)

            for s in bboxes.get("signatures", []):
                s_copy = dict(s)
                s_copy["page_number"] = page_number
                all_signatures.append(s_copy)

            for q in bboxes.get("qr_codes", []):
                q_copy = dict(q)
                q_copy["page_number"] = page_number
                all_qr_codes.append(q_copy)

            if sd.get("is_estamp_document"):
                is_estamp = True

            page_fields = sd.get("document_fields", {})
            page_score = page_fields.get("estamp_score", 0)
            if page_score > best_estamp_score:
                best_estamp_score = page_score
                document_fields = page_fields

        return {
            "success": True,
            "is_estamp_document": is_estamp,
            "document_type": "e_stamp" if is_estamp else "non_e_stamp",
            "document_fields": document_fields,
            "physical_stamps_found": len(all_stamps),
            "signatures_found": len(all_signatures),
            "bounding_boxes": {
                "stamps": all_stamps,
                "signatures": all_signatures,
                "qr_codes": all_qr_codes,
            },
        }

    def _save_detection_visualization(
        self,
        image,
        stamp_result: Dict[str, Any],
        output_dir: str,
        filename: str,
        page_number: Optional[int] = None,
    ) -> None:
        """Draw bounding boxes on image and save annotated PNG to output_dir."""
        try:
            from app.stamp_detection.utils import StampDetectionUtils

            detections = stamp_result.get("raw_detections", [])
            if not detections:
                return

            annotated = StampDetectionUtils.draw_detections(image, detections)

            base = os.path.splitext(filename)[0]
            if page_number is not None:
                viz_name = f"{base}_page{page_number}_detections.png"
            else:
                viz_name = f"{base}_detections.png"

            os.makedirs(output_dir, exist_ok=True)
            viz_path = os.path.join(output_dir, viz_name)
            cv2.imwrite(viz_path, annotated)
            logger.info(f"Saved detection visualization to {viz_path}")

        except Exception as e:
            logger.warning(f"Failed to save visualization: {e}")

    # ------------------------------------------------------------------
    # Modular pipeline step helpers
    # ------------------------------------------------------------------

    def _run_address_extraction(
        self, doc_id: str, formatted_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract address from OCR text. Isolated for testability."""
        logger.info(f"Running address extraction for {doc_id}")
        try:
            ocr_text = formatted_result.get("text", "")
            extracted_address = AddressExtractor.extract_from_text(ocr_text)
            return extracted_address or {}
        except Exception as addr_err:
            logger.warning(f"Address extraction failed for {doc_id}: {addr_err}")
            return {"error": str(addr_err)}

    def _run_field_validation(
        self, doc_id: str, classification_result
    ) -> Dict[str, Any]:
        """Validate extracted fields against doc-type rules. Isolated for testability."""
        logger.info(f"Running field validation for {doc_id}")
        try:
            doc_type = classification_result.document_type
            fields = classification_result.extracted_fields
            if fields:
                return validate_extracted_fields(doc_type, fields)
            return {"valid": True, "results": {}}
        except Exception as val_err:
            logger.warning(f"Field validation failed for {doc_id}: {val_err}")
            return {"valid": False, "error": str(val_err)}

    def process_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        doc_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a document from bytes (e.g., for testing).

        Writes bytes to temp file, processes, then cleans up.

        Args:
            file_bytes: Raw image bytes.
            filename: Original filename.
            doc_id: Optional document ID.
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
                filename=filename,
                **kwargs
            )
        finally:
            try:
                os.unlink(tmp.name)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp.name}: {e}")
