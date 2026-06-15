# app/stamp_detection/anomaly_detector.py
#
# Per-crop anomaly detection for stamp images.
#
# Extracted from detector.py — this module handles:
#   - Faded stamp detection (low standard deviation)
#   - Low contrast detection (narrow intensity range)
#   - Blurry stamp detection (low Laplacian variance)
#
# All methods are stateless and operate on individual crop images.

import cv2
import numpy as np
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detect suspicious visual patterns in stamp crop images.

    Each check operates on a single BGR crop and returns a boolean.
    The main entry point `detect_anomalies()` iterates over a list
    of detection dicts and annotates them in-place.
    """

    # --- Thresholds ---
    FADED_STD_THRESHOLD = 30       # std-dev below this → faded
    LOW_CONTRAST_RANGE_THRESHOLD = 50  # intensity range below this → low contrast
    BLUR_LAPLACIAN_THRESHOLD = 100     # Laplacian variance below this → blurry

    @staticmethod
    def detect_anomalies(detections: List[Dict]) -> List[Dict]:
        """
        Detect suspicious patterns in stamp crops.

        Iterates over detections, checks only those labelled "stamp"
        that have a crop image, and populates the 'anomalies' list.

        Args:
            detections: List of detection dicts (must have 'label', 'crop',
                        and 'anomalies' keys).

        Returns:
            The same list with 'anomalies' populated in-place.
        """
        for detection in detections:
            anomalies = []
            crop = detection.get("crop")

            if detection.get("label") != "stamp" or crop is None:
                continue

            if AnomalyDetector.is_faded_stamp(crop):
                anomalies.append("faded_stamp")

            if AnomalyDetector.is_low_contrast(crop):
                anomalies.append("low_contrast")

            if AnomalyDetector.is_blurry(crop):
                anomalies.append("blurry_stamp")

            detection["anomalies"] = anomalies

        return detections

    @staticmethod
    def is_faded_stamp(crop: np.ndarray) -> bool:
        """Check if stamp appears faded (low standard deviation in grayscale)."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return np.std(gray) < AnomalyDetector.FADED_STD_THRESHOLD

    @staticmethod
    def is_low_contrast(crop: np.ndarray) -> bool:
        """Check if image has low contrast (narrow intensity range)."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return (gray.max() - gray.min()) < AnomalyDetector.LOW_CONTRAST_RANGE_THRESHOLD

    @staticmethod
    def is_blurry(crop: np.ndarray) -> bool:
        """Check if stamp is blurry (low Laplacian variance)."""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return laplacian.var() < AnomalyDetector.BLUR_LAPLACIAN_THRESHOLD
