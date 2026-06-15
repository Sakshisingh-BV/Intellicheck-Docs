# stamp_detection/detector.py - YOLO DETECTION & ORCHESTRATION
#
# This module handles:
#   1. YOLO object detection (stamp / signature localisation)
#   2. Orchestration — delegates to specialised modules:
#      - EStampClassifier  for document classification + field extraction
#      - AnomalyDetector   for per-crop anomaly checks
#      - StampDetectionUtils for cropping, ink checks, and visualisation

import cv2
import numpy as np
import torch
import logging
import os
from typing import List, Dict, Optional

os.environ.setdefault(
    "YOLO_CONFIG_DIR",
    os.path.abspath(os.path.join(os.getcwd(), ".ultralytics")),
)

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

try:
    from .estamp_classifier import EStampClassifier
except ImportError:
    from estamp_classifier import EStampClassifier

try:
    from .anomaly_detector import AnomalyDetector
except ImportError:
    from anomaly_detector import AnomalyDetector

# Import OCREngine for dependency injection into EStampClassifier
try:
    from app.ocr.engine import OCREngine
    HAS_OCR = True
except ImportError:
    try:
        from ..ocr.engine import OCREngine
        HAS_OCR = True
    except ImportError:
        HAS_OCR = False
        logger.warning("OCREngine not available — e-stamp text extraction disabled")

# Import QRProcessor for dependency injection into EStampClassifier
try:
    from .qr_processor import QRProcessor
    HAS_QR_PROCESSOR = True
except ImportError:
    try:
        from qr_processor import QRProcessor
        HAS_QR_PROCESSOR = True
    except ImportError:
        HAS_QR_PROCESSOR = False
        logger.warning("QRProcessor not available — barcode processing disabled")


class StampDetector:
    """
    Stamp Detection with Independent Document Classification & Object Detection

    Architecture:
        Document classification and object detection are fully independent:

        1. YOLO detects physical stamps and signatures (object detection).
           - Stamps remain "stamp", signatures remain "signature".
           - YOLO labels are NEVER relabeled based on document type.

        2. EStampClassifier handles document-level e-stamp classification
           via full-page OCR + weighted scoring (see estamp_classifier.py).

        3. AnomalyDetector checks per-crop image quality
           (faded, low contrast, blurry — see anomaly_detector.py).

        A document can simultaneously be:
            - document_type = "e_stamp"
            - physical_stamps > 0
            - signatures > 0
    """

    # Model may use "sign"; app API uses "signature"
    _MODEL_LABEL_TO_APP = {
        "stamp": "stamp",
        "sign": "signature",
        "signature": "signature",
    }

    def __init__(self, model_path: str = "app/models/best.pt",
                 confidence_threshold: float = 0.5,
                 signature_confidence_threshold: float = 0.5,
                 ocr_engine=None):
        """Initialize detector — loads YOLO model and creates sub-modules.

        Args:
            model_path: Path to YOLO model
            confidence_threshold: Threshold for stamps (default 0.5)
            signature_confidence_threshold: Threshold for signatures (default 0.5)
            ocr_engine: Optional pre-initialised OCREngine to reuse
        """

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")

        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.signature_confidence_threshold = signature_confidence_threshold
        logger.info(f"YOLO class names: {self.model.names}")

        # Reuse passed-in OCR engine, or create a new one
        if ocr_engine is not None:
            logger.info("Reusing shared OCREngine for e-stamp text extraction")
        elif HAS_OCR:
            try:
                ocr_engine = OCREngine()
                logger.info("OCREngine initialised for e-stamp text extraction")
            except Exception as e:
                logger.warning(f"Failed to initialise OCREngine: {e}")

        # Initialise QR processor (shared with EStampClassifier)
        qr_processor = None
        if HAS_QR_PROCESSOR:
            qr_processor = QRProcessor()
            logger.info("QRProcessor initialised (Data Matrix + QR detection/decoding)")

        # Initialise e-stamp classifier with injected dependencies
        self.estamp_classifier = EStampClassifier(
            ocr_engine=ocr_engine,
            qr_processor=qr_processor,
        )

        logger.info("✅ Enhanced Stamp Detector loaded (document-level e-stamp support)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image_input, return_crops: bool = True,
               ocr_text: Optional[str] = None) -> Dict:
        """
        Detect stamps/signatures and classify document type independently.

        Args:
            image_input: Image path (str) or numpy array (BGR)
            return_crops: Whether to include cropped images in results
            ocr_text: Optional pre-extracted OCR text to skip redundant OCR

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
            image = self._load_image(image_input)

            # Step 1: YOLO detection (stamp / signature localisation)
            detections = self._run_yolo(image, return_crops)

            # Step 2: E-stamp classification (OCR + QR + scoring)
            estamp_result = self.estamp_classifier.classify(
                image, ocr_text=ocr_text
            )

            # Step 3: Anomaly checks (per-crop)
            detections = AnomalyDetector.detect_anomalies(detections)

            # Step 4: Build summary (physical objects only)
            summary = self._create_summary(detections)

            return {
                "document_type": estamp_result["document_type"],
                "is_estamp_document": estamp_result["is_estamp_document"],
                "document_fields": estamp_result["document_fields"],
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
                    "qr_certificate_match": None,
                    "qr_certificate_number": None,
                    "estamp_score": 0,
                    "estamp_threshold": self.estamp_classifier.ESTAMP_THRESHOLD,
                    "scoring_breakdown": {},
                    "blur_score": None,
                    "blur_level": "unknown",
                    "ocr_retried": False,
                },
                "detections": [],
                "summary": {
                    "total_detections": 0,
                    "physical_stamps": 0,
                    "signatures": 0,
                    "detections_with_anomalies": 0,
                    "overall_confidence": 0.0,
                    "error": str(e),
                },
                "image_shape": None
            }

    # ------------------------------------------------------------------
    # Image Loading
    # ------------------------------------------------------------------

    def _load_image(self, image_input) -> np.ndarray:
        """Load image from path or pass through numpy array."""
        if isinstance(image_input, str):
            image = cv2.imread(image_input)
        else:
            image = image_input

        if image is None:
            raise ValueError("Could not load image")

        return image

    # ------------------------------------------------------------------
    # YOLO Detection
    # ------------------------------------------------------------------

    def _run_yolo(self, image: np.ndarray, return_crops: bool) -> List[Dict]:
        """Run YOLO model and parse detections with per-class thresholds."""
        min_conf = min(self.confidence_threshold, self.signature_confidence_threshold)
        results = self.model(image, conf=min_conf)
        return self._parse_detections(
            image, results[0], return_crops,
            stamp_conf=self.confidence_threshold,
            sig_conf=self.signature_confidence_threshold,
        )

    def _parse_detections(self, image: np.ndarray, result, return_crops: bool,
                          stamp_conf: float = 0.5, sig_conf: float = 0.5) -> List[Dict]:
        """Parse YOLO results into detection dicts with per-class thresholds.

        Args:
            image: Input image
            result: YOLO result object
            return_crops: Whether to return cropped images
            stamp_conf: Confidence threshold for stamps
            sig_conf: Confidence threshold for signatures
        """
        detections = []

        if result.boxes is None or len(result.boxes) == 0:
            return detections

        for i in range(len(result.boxes)):
            try:
                boxes = result.boxes
                class_id = int(boxes.cls[i])
                confidence = float(boxes.conf[i])
                bbox = boxes.xyxy[i].cpu().numpy().tolist()

                label = self._resolve_detection_label(class_id)
                if label == "unknown":
                    logger.debug(
                        f"Skipping unmapped class_id={class_id} "
                        f"(model name={self.model.names.get(class_id)!r})"
                    )
                    continue

                # Apply per-class confidence thresholds
                if label == "stamp":
                    if confidence < stamp_conf:
                        logger.debug(f"Filtered stamp with confidence {confidence:.3f} < {stamp_conf}")
                        continue
                elif label == "signature":
                    if confidence < sig_conf:
                        logger.debug(f"Filtered signature with confidence {confidence:.3f} < {sig_conf}")
                        continue

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

    def _resolve_detection_label(self, class_id: int) -> str:
        """Map YOLO class id to app label (stamp / signature)."""
        raw_label = self.model.names.get(class_id, "")
        if isinstance(raw_label, int):
            raw_label = self.model.names.get(raw_label, "")
        return self._MODEL_LABEL_TO_APP.get(str(raw_label).lower().strip(), "unknown")

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
