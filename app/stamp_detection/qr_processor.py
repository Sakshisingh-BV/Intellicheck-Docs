# app/stamp_detection/qr_processor.py

import cv2
import numpy as np
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class QRProcessor:
    """
    Simplified QR code detection and decoding using OpenCV.
    
    This processor focuses exclusively on standard QR codes using OpenCV's built-in 
    QRCodeDetector, avoiding heavy third-party barcode libraries (like pylibdmtx or pyzbar)
    and complex progressive multi-region cropping.
    """

    def process(self, image: np.ndarray, is_likely_estamp: bool = False) -> Dict:
        """
        Detect QR presence and decode QR payload using OpenCV.
        
        Returns:
            {
                "qr_present":    bool,
                "qr_decoded":    bool,
                "qr_data":       str | None,
                "decode_method": str | None,
            }
        """
        result: Dict = {
            "qr_present": False,
            "qr_decoded": False,
            "qr_data": None,
            "decode_method": None,
        }

        if image is None:
            return result

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        if gray.dtype != np.uint8:
            gray = np.clip(gray, 0, 255).astype(np.uint8)

        # Step 1: Detect and Decode using OpenCV QRCodeDetector
        try:
            detector = cv2.QRCodeDetector()
            val, points, _ = detector.detectAndDecode(gray)
            if val:
                result.update(
                    qr_present=True,
                    qr_decoded=True,
                    qr_data=val.strip(),
                    decode_method="opencv_qrcode_detector"
                )
                logger.info("QR code decoded successfully via OpenCV QRCodeDetector")
                return result
        except Exception as e:
            logger.debug(f"OpenCV QR decode error: {e}")

        # Step 2: Visual presence check using OpenCV contour analysis (fallback to detector.detect)
        qr_present = self._detect_qr_presence(gray)
        result["qr_present"] = qr_present

        if qr_present:
            logger.info("QR code visually detected but could not be decoded")
        else:
            logger.debug("No QR code detected visually or decoded")

        return result

    def _detect_qr_presence(self, gray: np.ndarray) -> bool:
        """
        Lightweight contour-based check for QR presence using OpenCV.
        Looks for nested square-like contours typical of QR finder patterns.
        """
        try:
            # Thresholding to get binary image
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, blockSize=51, C=10
            )
            
            contours, hierarchy = cv2.findContours(
                binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )
            
            if hierarchy is None or len(contours) == 0:
                # Fallback to OpenCV QRCodeDetector's built-in detect
                try:
                    detector = cv2.QRCodeDetector()
                    retval, _ = detector.detect(gray)
                    return bool(retval)
                except Exception:
                    return False

            hierarchy = hierarchy[0]
            candidates = 0
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area < 40:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                if h == 0 or w == 0:
                    continue
                
                # QR finder patterns are square-like (aspect ratio ~1.0)
                aspect_ratio = float(w) / float(h)
                if not (0.4 <= aspect_ratio <= 2.5):
                    continue
                
                # Check for nesting: QR finder patterns have nested contours (child index is not -1)
                if hierarchy[i][2] == -1:
                    continue
                
                candidates += 1

            # A QR code contains 3 finder patterns; finding at least 2 suggests a QR presence
            is_present = candidates >= 2

            # Fallback check using OpenCV's built-in detector if contour check was negative
            if not is_present:
                try:
                    detector = cv2.QRCodeDetector()
                    retval, _ = detector.detect(gray)
                    is_present = bool(retval)
                except Exception:
                    pass

            return is_present

        except Exception as e:
            logger.debug(f"QR presence detection error: {e}")
            return False
