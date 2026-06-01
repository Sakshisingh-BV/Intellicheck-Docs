# stamp_detection/detector.py - SEPARATED DOCUMENT CLASSIFICATION & OBJECT DETECTION

import cv2
import numpy as np
import torch
import logging
import os
import re
from typing import List, Dict, Optional
from datetime import datetime

# Fix PyTorch 2.6+ security issue with model loading
_original_load = torch.load
def torch_load_with_globals(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _original_load(*args, **kwargs)
torch.load = torch_load_with_globals

from ultralytics import YOLO

logger = logging.getLogger(__name__)

try:
    from .utils import StampDetectionUtils
except ImportError:
    from utils import StampDetectionUtils

# Import the project's OCR engine + parser (PaddleOCR v3.5 compatible)
try:
    from app.ocr.engine import OCREngine
    from app.ocr.parser import OCRParser
    HAS_OCR = True
except ImportError:
    try:
        from ..ocr.engine import OCREngine
        from ..ocr.parser import OCRParser
        HAS_OCR = True
    except ImportError:
        HAS_OCR = False
        logger.warning("OCREngine not available — e-stamp text extraction disabled")

# Import blur assessment and sharpening for OCR retry logic
try:
    from app.preprocessing.blur import detect_blur, sharpen_image
    HAS_BLUR = True
except ImportError:
    try:
        from ..preprocessing.blur import detect_blur, sharpen_image
        HAS_BLUR = True
    except ImportError:
        HAS_BLUR = False
        logger.warning("Blur module not available — OCR retry on blurry images disabled")

# Optional: QR code reading
try:
    import pyzbar.pyzbar as pyzbar
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False
    logger.warning("pyzbar not installed — QR code reading disabled")


class StampDetector:
    """
    Stamp Detection with Independent Document Classification & Object Detection

    Architecture:
        Document classification and object detection are fully independent:

        1. YOLO detects physical stamps and signatures (object detection).
           - Stamps remain "stamp", signatures remain "signature".
           - YOLO labels are NEVER relabeled based on document type.

        2. Full-page OCR classifies the document type (document classification).
           - Weighted scoring determines if the document is an e-stamp.
           - Extracted fields (certificate_number, stamp_duty, state, date)
             are always returned for OCR debugging.

        A document can simultaneously be:
            - document_type = "e_stamp"
            - physical_stamps > 0
            - signatures > 0

    Scoring weights:
        certificate_number = 40
        stamp_duty         = 25
        state              = 15
        date               = 10
        qr_present         =  5   (contour-based, weak signal)
        qr_decoded         =  5   (pyzbar decode, strong signal)
        threshold          = 50
    """

    CLASS_NAMES = {
        15: "stamp",
        16: "signature"
    }

    # --- Weighted scoring configuration ---
    ESTAMP_WEIGHTS = {
        "certificate_number": 40,
        "stamp_duty": 25,
        "state": 15,
        "date": 10,
        "qr_present": 5,    # weak signal: contour-based presence
        "qr_decoded": 5,    # strong signal: pyzbar full decode
    }
    ESTAMP_THRESHOLD = 50

    # --- OCR quality thresholds for blur-aware retry ---
    OCR_MIN_CHARS = 100     # minimum chars for "acceptable" OCR
    OCR_MIN_BLOCKS = 5      # minimum text blocks for "acceptable" OCR

    # Indian states recognised in e-stamp documents
    KNOWN_STATES = [
        'Maharashtra', 'Gujarat', 'Karnataka', 'Tamil Nadu', 'Delhi',
        'Uttar Pradesh', 'West Bengal', 'Rajasthan', 'Punjab',
        'Andhra Pradesh', 'Telangana', 'Kerala', 'Madhya Pradesh',
        'Bihar', 'Odisha', 'Haryana', 'Himachal Pradesh', 'Jharkhand',
        'Chhattisgarh', 'Uttarakhand', 'Goa', 'Assam'
    ]

    def __init__(self, model_path: str = "app/models/best.pt",
                 confidence_threshold: float = 0.5):
        """Initialize detector — uses project OCREngine (PaddleOCR v3.5)."""

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")

        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold

        # Reuse the project-wide OCR engine (PaddleOCR v3.5 compatible)
        if HAS_OCR:
            try:
                self.ocr_engine = OCREngine()
                logger.info("OCREngine initialised for e-stamp text extraction")
            except Exception as e:
                logger.warning(f"Failed to initialise OCREngine: {e}")
                self.ocr_engine = None
        else:
            self.ocr_engine = None

        logger.info("✅ Enhanced Stamp Detector loaded (document-level e-stamp support)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image_input, return_crops: bool = True) -> Dict:
        """
        Detect stamps/signatures and classify document type independently.

        Returns:
        {
            "document_type": "e_stamp" | "non_e_stamp",
            "is_estamp_document": bool,
            "document_fields": {              # always present for debugging
                "certificate_number": str | None,
                "stamp_duty": str | None,
                "state": str | None,
                "date": str | None,
                "qr_present": bool,
                "qr_decoded": bool,
                "qr_data": str | None,
                "estamp_score": int,
                "estamp_threshold": int,
                "scoring_breakdown": { ... }
            },
            "detections": [ ... ],            # YOLO physical objects only
            "summary": {
                "total_detections": int,
                "physical_stamps": int,
                "signatures": int,
                "detections_with_anomalies": int,
                "overall_confidence": float
            },
            "image_shape": (h, w, c)
        }
        """

        try:
            # Load image
            if isinstance(image_input, str):
                image = cv2.imread(image_input)
            else:
                image = image_input

            if image is None:
                raise ValueError("Could not load image")

            # ----------------------------------------------------------
            # Step 1: Run YOLO detection (stamp / signature localization)
            # ----------------------------------------------------------
            results = self.model(image, conf=self.confidence_threshold)
            detections = self._parse_detections(image, results[0], return_crops)

            # ----------------------------------------------------------
            # Step 2: Full-page OCR with blur-aware retry
            # ----------------------------------------------------------
            full_text, blur_info = self._run_full_page_ocr(image)

            # ----------------------------------------------------------
            # Step 3: QR detection (presence + decoding, independent)
            # ----------------------------------------------------------

            # 3a. QR presence detection (contour-based, works on low-res)
            qr_present = self._detect_qr_presence(image)

            # 3b. QR decoding via pyzbar (requires high-res)
            qr_decoded = False
            qr_data = None
            for det in detections:
                if det["label"] == "stamp" and det.get("crop") is not None:
                    data = self._read_qr_code(det["crop"])
                    if data:
                        qr_decoded = True
                        qr_data = data
                        break
            if not qr_decoded:
                data = self._read_qr_code(image)
                if data:
                    qr_decoded = True
                    qr_data = data

            logger.info(
                f"QR detection: qr_present={qr_present}, "
                f"qr_decoded={qr_decoded}"
            )

            # ----------------------------------------------------------
            # Step 4: Weighted scoring → is this an e-stamp document?
            # ----------------------------------------------------------
            estamp_score, estamp_details = self._compute_estamp_score(
                full_text, qr_present, qr_decoded
            )

            is_estamp_document = estamp_score >= self.ESTAMP_THRESHOLD

            document_type = "e_stamp" if is_estamp_document else "non_e_stamp"

            logger.info(
                f"E-stamp score: {estamp_score}/{sum(self.ESTAMP_WEIGHTS.values())} "
                f"(threshold={self.ESTAMP_THRESHOLD}) → "
                f"document_type={document_type}"
            )

            # ----------------------------------------------------------
            # Step 5: Anomaly checks (per-crop)
            # ----------------------------------------------------------
            detections = self._detect_anomalies(detections)

            # ----------------------------------------------------------
            # Step 6: Build summary (physical objects only)
            # ----------------------------------------------------------
            summary = self._create_summary(detections)

            # ----------------------------------------------------------
            # Step 7: Build document_fields (ALWAYS returned for debugging)
            # ----------------------------------------------------------
            document_fields = {
                "certificate_number": estamp_details.get("certificate_number"),
                "stamp_duty": estamp_details.get("stamp_duty_value"),
                "state": estamp_details.get("state"),
                "date": estamp_details.get("date"),
                "qr_present": qr_present,
                "qr_decoded": qr_decoded,
                "qr_data": qr_data,
                "estamp_score": estamp_score,
                "estamp_threshold": self.ESTAMP_THRESHOLD,
                "scoring_breakdown": estamp_details.get("scoring_breakdown", {}),
                "blur_score": blur_info.get("blur_score"),
                "blur_level": blur_info.get("blur_level"),
                "ocr_retried": blur_info.get("ocr_retried", False),
            }

            return {
                "document_type": document_type,
                "is_estamp_document": is_estamp_document,
                "document_fields": document_fields,
                "detections": detections,
                "summary": summary,
                "image_shape": image.shape
            }

        except Exception as e:
            logger.error(f"Error during detection: {e}")
            return {
                "document_type": "non_e_stamp",
                "is_estamp_document": False,
                "document_fields": {
                    "certificate_number": None,
                    "stamp_duty": None,
                    "state": None,
                    "date": None,
                    "qr_present": False,
                    "qr_decoded": False,
                    "qr_data": None,
                    "estamp_score": 0,
                    "estamp_threshold": self.ESTAMP_THRESHOLD,
                    "scoring_breakdown": {},
                    "blur_score": None,
                    "blur_level": "unknown",
                    "ocr_retried": False,
                },
                "detections": [],
                "summary": {"error": str(e)},
                "image_shape": None
            }

    # ------------------------------------------------------------------
    # YOLO Parsing
    # ------------------------------------------------------------------

    def _parse_detections(self, image: np.ndarray, result, return_crops: bool) -> List[Dict]:
        """Parse YOLO results into detection dicts."""
        detections = []

        if result.boxes is None or len(result.boxes) == 0:
            return detections

        for i in range(len(result.boxes)):
            try:
                boxes = result.boxes
                class_id = int(boxes.cls[i])
                confidence = float(boxes.conf[i])
                bbox = boxes.xyxy[i].cpu().numpy().tolist()

                label = self.CLASS_NAMES.get(class_id, "unknown")
                crop = StampDetectionUtils.crop_detection(image, bbox)

                # Check coloured ink (physical stamp indicator)
                has_ink = True
                if label == "stamp" and crop is not None:
                    has_ink = StampDetectionUtils.has_colored_ink(crop)

                detection = {
                    "label": label,
                    "confidence": round(confidence, 3),
                    "bbox": [round(x, 2) for x in bbox],
                    "ink_confirmed": has_ink,
                    "crop": crop if return_crops else None,
                    "anomalies": []
                }

                detections.append(detection)

            except Exception as e:
                logger.warning(f"Error parsing detection: {e}")
                continue

        return detections

    # ------------------------------------------------------------------
    # Full-Page OCR (PaddleOCR v3.5 via OCREngine)
    # ------------------------------------------------------------------

    def _run_full_page_ocr(self, image: np.ndarray) -> tuple:
        """
        Run OCR on the full document image with blur-aware retry.

        Flow:
            1. Assess blur (if blur module available).
            2. OCR on the original image.
            3. If image is blurry AND OCR quality is poor:
               → sharpen image → retry OCR → use better result.

        Uses the project's OCREngine (PaddleOCR v3.5 predict() API)
        and OCRParser to extract text.

        Returns:
            (full_text: str, blur_info: dict)
            blur_info keys: blur_score, blur_level, is_blurry, ocr_retried
        """
        default_blur_info = {
            "blur_score": None,
            "blur_level": "unknown",
            "is_blurry": False,
            "ocr_retried": False,
        }

        if self.ocr_engine is None:
            logger.debug("OCREngine not available — skipping full-page OCR")
            return "", default_blur_info

        try:
            # --- Step 1: Blur assessment ---
            blur_info = dict(default_blur_info)
            if HAS_BLUR:
                try:
                    blur_result = detect_blur(image)
                    blur_info["blur_score"] = blur_result["blur_score"]
                    blur_info["blur_level"] = blur_result["blur_level"]
                    blur_info["is_blurry"] = blur_result["is_blurry"]
                    logger.debug(
                        f"Blur assessment: score={blur_result['blur_score']}, "
                        f"level={blur_result['blur_level']}"
                    )
                except Exception as e:
                    logger.warning(f"Blur assessment failed: {e}")

            # --- Step 2: OCR on original image ---
            raw_result = self.ocr_engine.extract(image)
            parsed = OCRParser.parse(raw_result)
            full_text = " ".join(
                block.get("text", "") for block in parsed
            ).strip()

            logger.debug(
                f"Full-page OCR (original): {len(parsed)} blocks, "
                f"{len(full_text)} chars"
            )

            # --- Step 3: Retry with sharpened image if needed ---
            if (
                HAS_BLUR
                and blur_info["is_blurry"]
                and not self._assess_ocr_quality(full_text, parsed)
            ):
                logger.info(
                    f"Blurry image (score={blur_info['blur_score']}) with "
                    f"poor OCR ({len(full_text)} chars, {len(parsed)} blocks) "
                    f"— retrying with sharpened image"
                )
                try:
                    sharpened = sharpen_image(image)
                    raw_retry = self.ocr_engine.extract(sharpened)
                    parsed_retry = OCRParser.parse(raw_retry)
                    retry_text = " ".join(
                        block.get("text", "") for block in parsed_retry
                    ).strip()

                    logger.info(
                        f"OCR retry result: {len(parsed_retry)} blocks, "
                        f"{len(retry_text)} chars "
                        f"(original: {len(parsed)} blocks, {len(full_text)} chars)"
                    )

                    # Use retry result only if it's genuinely better
                    if len(retry_text) > len(full_text):
                        full_text = retry_text
                        blur_info["ocr_retried"] = True
                        logger.info("Using sharpened OCR result (more text extracted)")
                    else:
                        logger.info("Sharpened OCR not better — keeping original result")

                except Exception as e:
                    logger.warning(f"OCR retry with sharpened image failed: {e}")

            return full_text, blur_info

        except Exception as e:
            logger.warning(f"Full-page OCR failed: {e}")
            return "", default_blur_info

    def _assess_ocr_quality(self, full_text: str, parsed_blocks: list) -> bool:
        """
        Assess whether OCR extraction quality is acceptable.

        Returns:
            True if quality is acceptable (enough text extracted).
            False if quality is poor (retry may be warranted).
        """
        char_count = len(full_text)
        block_count = len(parsed_blocks)

        is_acceptable = (
            char_count >= self.OCR_MIN_CHARS
            and block_count >= self.OCR_MIN_BLOCKS
        )

        logger.debug(
            f"OCR quality: {char_count} chars (min={self.OCR_MIN_CHARS}), "
            f"{block_count} blocks (min={self.OCR_MIN_BLOCKS}) → "
            f"{'acceptable' if is_acceptable else 'poor'}"
        )
        return is_acceptable

    # ------------------------------------------------------------------
    # E-Stamp Weighted Scoring
    # ------------------------------------------------------------------

    def _compute_estamp_score(self, full_text: str,
                              qr_present: bool,
                              qr_decoded: bool) -> tuple:
        """
        Compute a weighted e-stamp score from full-page OCR text.

        Weights:
            certificate_number  = 40
            stamp_duty          = 25
            state               = 15
            date                = 10
            qr_present          =  5  (contour-based, weak signal)
            qr_decoded          =  5  (pyzbar full decode, strong signal)

        Returns:
            (score: int, details: dict)
        """
        score = 0
        breakdown = {}

        # --- Certificate number (weight 40) ---
        cert_number = self._extract_cert_number(full_text)
        if cert_number:
            score += self.ESTAMP_WEIGHTS["certificate_number"]
            breakdown["certificate_number"] = {
                "found": True, "value": cert_number,
                "points": self.ESTAMP_WEIGHTS["certificate_number"]
            }
        else:
            breakdown["certificate_number"] = {"found": False, "points": 0}

        # --- Stamp duty value (weight 25) ---
        stamp_value = self._extract_stamp_value(full_text)
        if stamp_value:
            score += self.ESTAMP_WEIGHTS["stamp_duty"]
            breakdown["stamp_duty"] = {
                "found": True, "value": stamp_value,
                "points": self.ESTAMP_WEIGHTS["stamp_duty"]
            }
        else:
            breakdown["stamp_duty"] = {"found": False, "points": 0}

        # --- State (weight 15) ---
        state = self._extract_state(full_text)
        if state:
            score += self.ESTAMP_WEIGHTS["state"]
            breakdown["state"] = {
                "found": True, "value": state,
                "points": self.ESTAMP_WEIGHTS["state"]
            }
        else:
            breakdown["state"] = {"found": False, "points": 0}

        # --- Date (weight 10) ---
        date = self._extract_date(full_text)
        if date:
            score += self.ESTAMP_WEIGHTS["date"]
            breakdown["date"] = {
                "found": True, "value": date,
                "points": self.ESTAMP_WEIGHTS["date"]
            }
        else:
            breakdown["date"] = {"found": False, "points": 0}

        # --- QR presence (weight 5, weak signal) ---
        if qr_present:
            score += self.ESTAMP_WEIGHTS["qr_present"]
            breakdown["qr_present"] = {
                "found": True,
                "points": self.ESTAMP_WEIGHTS["qr_present"]
            }
        else:
            breakdown["qr_present"] = {"found": False, "points": 0}

        # --- QR decoded (weight 5, strong signal) ---
        if qr_decoded:
            score += self.ESTAMP_WEIGHTS["qr_decoded"]
            breakdown["qr_decoded"] = {
                "found": True,
                "points": self.ESTAMP_WEIGHTS["qr_decoded"]
            }
        else:
            breakdown["qr_decoded"] = {"found": False, "points": 0}

        details = {
            "certificate_number": cert_number,
            "stamp_duty_value": stamp_value,
            "state": state,
            "date": date,
            "scoring_breakdown": breakdown,
        }

        return score, details

    # ------------------------------------------------------------------
    # Text Field Extractors (operate on full-page text string)
    # ------------------------------------------------------------------

    def _extract_cert_number(self, text: str) -> Optional[str]:
        """
        Extract e-stamp certificate number.

        Common formats:
            IN-MH12345678901234   (SHCIL format)
            MH-240101-123456      (state-date-serial)
            Certificate No: XXXXX
        """
        if not text:
            return None

        patterns = [
            r'IN-[A-Z]{2}\d{14,20}',                   # SHCIL format
            r'[A-Z]{2,3}-\d{6}-\d{6}',                  # State-date-serial
            r'[Cc]ertificate\s*(?:[Nn]o\.?|#)\s*[:.]?\s*([A-Z0-9\-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0) if match.lastindex is None else match.group(1)

        return None

    def _extract_stamp_value(self, text: str) -> Optional[str]:
        """Extract stamp duty value (e.g. Rs. 100, INR 500, ₹ 1,000.00)."""
        if not text:
            return None

        patterns = [
            r'(?:Rs\.?|INR|₹)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'[Ss]tamp\s*[Dd]uty\s*(?:of|:)?\s*(?:Rs\.?|INR|₹)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_state(self, text: str) -> Optional[str]:
        """Extract issuing state from text."""
        if not text:
            return None

        text_lower = text.lower()
        for state in self.KNOWN_STATES:
            if state.lower() in text_lower:
                return state

        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract issue date from text."""
        if not text:
            return None

        patterns = [
            r'(\d{2}[/-]\d{2}[/-]\d{4})',   # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{4}[/-]\d{2}[/-]\d{2})',    # YYYY-MM-DD
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    # ------------------------------------------------------------------
    # QR Code: Presence Detection (contour-based, works on low-res)
    # ------------------------------------------------------------------

    def _detect_qr_presence(self, image: np.ndarray) -> bool:
        """
        Detect if a QR-like pattern is visually present in the image.

        Uses contour analysis to find QR finder patterns (nested squares).
        Does NOT decode the QR data — only checks for the visual pattern.
        Works on low-resolution images where pyzbar fails.

        A QR code has 3 finder patterns (concentric squares) at corners.
        We look for square-ish contours that contain nested child squares.
        If we find >= 2 such patterns, we consider QR present.
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            # Adaptive threshold handles varying lighting
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=51,
                C=10
            )

            contours, hierarchy = cv2.findContours(
                binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )

            if hierarchy is None:
                return False

            hierarchy = hierarchy[0]  # shape: (N, 4) — [next, prev, child, parent]

            finder_candidates = 0

            for i, contour in enumerate(contours):
                # Skip tiny contours (noise)
                area = cv2.contourArea(contour)
                if area < 100:
                    continue

                # Check if contour is roughly square
                x, y, w, h = cv2.boundingRect(contour)
                if h == 0 or w == 0:
                    continue
                aspect_ratio = float(w) / float(h)
                if not (0.7 <= aspect_ratio <= 1.3):
                    continue

                # Check for nested structure (parent → child → grandchild)
                # QR finder pattern = 3 levels of nesting
                child_idx = hierarchy[i][2]
                if child_idx == -1:
                    continue

                # Check child is also roughly square
                child_contour = contours[child_idx]
                child_area = cv2.contourArea(child_contour)
                if child_area < 30:
                    continue
                cx, cy, cw, ch = cv2.boundingRect(child_contour)
                if ch == 0 or cw == 0:
                    continue
                child_aspect = float(cw) / float(ch)
                if not (0.6 <= child_aspect <= 1.4):
                    continue

                # Check grandchild exists (3-level nesting)
                grandchild_idx = hierarchy[child_idx][2]
                if grandchild_idx != -1:
                    finder_candidates += 1

            # QR code has 3 finder patterns; >= 2 is strong evidence
            is_present = finder_candidates >= 2
            logger.debug(
                f"QR presence: {finder_candidates} finder-like patterns → "
                f"{'present' if is_present else 'not found'}"
            )
            return is_present

        except Exception as e:
            logger.debug(f"QR presence detection error: {e}")
            return False

    # ------------------------------------------------------------------
    # QR Code: Decoding (pyzbar, requires high-res)
    # ------------------------------------------------------------------

    def _read_qr_code(self, image: np.ndarray) -> Optional[str]:
        """Attempt to fully decode QR data from image using pyzbar."""
        if not HAS_PYZBAR:
            return None

        try:
            decoded = pyzbar.decode(image)
            if decoded:
                return decoded[0].data.decode('utf-8')
            return None
        except Exception as e:
            logger.debug(f"QR decode error: {e}")
            return None

    # ------------------------------------------------------------------
    # Anomaly Detection (per-crop)
    # ------------------------------------------------------------------

    def _detect_anomalies(self, detections: List[Dict]) -> List[Dict]:
        """Detect suspicious patterns in stamp crops."""

        for detection in detections:
            anomalies = []
            crop = detection.get("crop")

            if crop is None:
                continue

            if self._is_faded_stamp(crop):
                anomalies.append("faded_stamp")

            if self._is_low_contrast(crop):
                anomalies.append("low_contrast")

            if self._is_blurry(crop):
                anomalies.append("blurry_stamp")

            detection["anomalies"] = anomalies

        return detections

    def _is_faded_stamp(self, crop: np.ndarray) -> bool:
        """Check if stamp appears faded."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return np.std(gray) < 30

    def _is_low_contrast(self, crop: np.ndarray) -> bool:
        """Check if image has low contrast."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return (gray.max() - gray.min()) < 50

    def _is_blurry(self, crop: np.ndarray) -> bool:
        """Check if stamp is blurry."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return laplacian.var() < 100

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _create_summary(self, detections: List[Dict]) -> Dict:
        """Create summary statistics (physical objects only)."""

        physical_stamps = [d for d in detections if d["label"] == "stamp"]
        signatures = [d for d in detections if d["label"] == "signature"]
        anomalies_count = sum(1 for d in detections if d.get("anomalies"))

        return {
            "total_detections": len(detections),
            "physical_stamps": len(physical_stamps),
            "signatures": len(signatures),
            "detections_with_anomalies": anomalies_count,
            "overall_confidence": round(
                np.mean([d["confidence"] for d in detections]) if detections else 0,
                3
            )
        }

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def visualize_detections(self, image_input, save_path: Optional[str] = None) -> np.ndarray:
        """Visualize detections with labels."""
        result = self.detect(image_input)

        if isinstance(image_input, str):
            image = cv2.imread(image_input)
        else:
            image = image_input.copy()

        annotated = StampDetectionUtils.draw_detections(image, result["detections"])

        if save_path:
            cv2.imwrite(save_path, annotated)
            logger.info(f"Visualization saved to {save_path}")

        return annotated