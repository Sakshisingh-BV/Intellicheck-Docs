# app/stamp_detection/qr_processor.py

import cv2
import numpy as np
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

try:
    from pylibdmtx.pylibdmtx import decode as _dmtx_decode
    HAS_DMTX = True
except ImportError:
    HAS_DMTX = False
    logger.warning("pylibdmtx not installed — pip install pylibdmtx")

try:
    import pyzbar.pyzbar as pyzbar
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False
    logger.warning("pyzbar not installed — pip install pyzbar")

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow not installed — pip install Pillow")


class QRProcessor:
    """
    Barcode detection and decoding for e-stamp documents.

    Decoder priority:
        1. pylibdmtx  — Data Matrix (primary: SHCIL e-stamps) — requires PIL
        2. pyzbar     — ZBar multi-format (QR, DataMatrix fallback)
        3. cv2        — OpenCV QRCodeDetector (QR only)

    Preprocessing levels per crop:
        0: Raw grayscale
        1: 2x upscale
        2: 2x upscale + adaptive threshold (NOT Otsu — preserves DM L-border)

    Crop regions (most-likely first):
        dm_zone     — SHCIL Data Matrix position (lower-left)
        mid_left    — wider fallback
        full_image  — last resort
    """

    QR_CROP_REGIONS = [
        (0.55, 0.82, 0.0, 0.38, "dm_zone"),
        (0.45, 0.85, 0.0, 0.45, "mid_left"),
        (0.0,  1.0,  0.0, 1.0,  "full_image"),
    ]

    def process(self, image: np.ndarray, is_likely_estamp: bool = False) -> Dict:
        """
        Entry point. Returns:
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

        # Step 1: Quick decode on full image — no preprocessing
        decoded = self._decode_barcode(image, "full_image")
        if decoded:
            data, method = decoded
            result.update(qr_present=True, qr_decoded=True,
                          qr_data=data, decode_method=method)
            logger.info(f"Barcode decoded on first attempt: method={method}")
            return result

        # Step 2: Visual presence check
        barcode_present = self._detect_barcode_presence(image)
        result["qr_present"] = barcode_present

        # Step 3: Region-crop + preprocessing pipeline
        if not (is_likely_estamp or barcode_present):
            logger.debug("Barcode enhanced pipeline skipped")
            return result

        logger.info(f"Triggering enhanced pipeline "
                    f"(is_likely_estamp={is_likely_estamp}, "
                    f"barcode_present={barcode_present})")

        crops = self._crop_regions(image)

        for region_img, region_label in crops:
            decoded = self._try_progressive_decode(region_img, region_label)
            if decoded:
                data, method = decoded
                result.update(qr_present=True, qr_decoded=True,
                              qr_data=data, decode_method=method)
                logger.info(f"Barcode decoded via enhanced pipeline: method={method}")
                return result

        h, w = image.shape[:2]
        min_crop_dim = min((min(c.shape[:2]) for c, _ in crops), default=0)
        if barcode_present and min_crop_dim < 150:
            logger.warning(
                f"Decode failed — image likely too low-res "
                f"({w}x{h}px, smallest crop={min_crop_dim}px). Use 300+ DPI."
            )
        else:
            logger.info("Enhanced pipeline exhausted — decode failed")

        return result

    def _try_progressive_decode(
        self, region_img: np.ndarray, region_label: str
    ) -> Optional[Tuple[str, str]]:
        """3-level pipeline. Stops at first success."""
        img = region_img
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        if gray.dtype != np.uint8:
            gray = np.clip(gray, 0, 255).astype(np.uint8)

        # Level 0: raw grayscale
        result = self._decode_barcode(gray, f"raw_{region_label}")
        if result:
            return result

        # Level 1: 2x upscale
        up = cv2.resize(gray, (gray.shape[1] * 2, gray.shape[0] * 2),
                        interpolation=cv2.INTER_CUBIC)
        result = self._decode_barcode(up, f"2x_{region_label}")
        if result:
            return result

        # Level 2: 2x upscale + adaptive threshold (preserves DM L-border)
        thresh = cv2.adaptiveThreshold(
            up, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 8
        )
        result = self._decode_barcode(thresh, f"thresh_{region_label}")
        if result:
            return result

        return None

    def _decode_barcode(
        self, image: np.ndarray, step_label: str
    ) -> Optional[Tuple[str, str]]:
        """
        Try all decoders on a single image.
        Returns (payload, method_label) or None.
        """
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Decoder 1: pylibdmtx — MUST use PIL Image, not raw numpy
        if HAS_DMTX and HAS_PIL:
            try:
                pil_img = PILImage.fromarray(gray)
                results = _dmtx_decode(pil_img, timeout=500)
                if results:
                    payload = results[0].data.decode("utf-8", errors="replace").strip()
                    if payload:
                        logger.debug(f"pylibdmtx [{step_label}]: {payload[:80]}")
                        return payload, f"dmtx_{step_label}"
            except Exception as e:
                logger.debug(f"pylibdmtx error [{step_label}]: {e}")

        # Decoder 2: pyzbar
        if HAS_PYZBAR:
            try:
                decoded_list = pyzbar.decode(gray)
                if decoded_list:
                    payload = decoded_list[0].data.decode("utf-8", errors="replace").strip()
                    if payload:
                        logger.debug(f"pyzbar [{step_label}] "
                                     f"type={decoded_list[0].type}: {payload[:80]}")
                        return payload, f"pyzbar_{step_label}"
            except Exception as e:
                logger.debug(f"pyzbar error [{step_label}]: {e}")

        # Decoder 3: OpenCV QR only
        try:
            val, _, _ = cv2.QRCodeDetector().detectAndDecode(gray)
            if val:
                logger.debug(f"opencv [{step_label}]: {val[:80]}")
                return val, f"opencv_{step_label}"
        except Exception as e:
            logger.debug(f"opencv error [{step_label}]: {e}")

        return None

    def _crop_regions(self, image: np.ndarray) -> List[Tuple[np.ndarray, str]]:
        """Crop likely barcode regions from document image."""
        h, w = image.shape[:2]
        crops = []
        for y1_r, y2_r, x1_r, x2_r, label in self.QR_CROP_REGIONS:
            y1, y2 = int(y1_r * h), int(y2_r * h)
            x1, x2 = int(x1_r * w), int(x2_r * w)
            region = image[y1:y2, x1:x2]
            if region.size > 0:
                crops.append((region, label))
        return crops

    def _detect_barcode_presence(self, image: np.ndarray) -> bool:
        """Lightweight contour-based check for QR or Data Matrix presence."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, blockSize=51, C=10
            )
            contours, hierarchy = cv2.findContours(
                binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )
            if hierarchy is None or len(contours) == 0:
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
                if not (0.4 <= float(w) / float(h) <= 2.5):
                    continue
                if hierarchy[i][2] == -1:
                    continue
                candidates += 1

            is_present = candidates >= 2
            logger.debug(f"Barcode presence: {candidates} candidates → "
                         f"{'detected' if is_present else 'not found'}")
            return is_present

        except Exception as e:
            logger.debug(f"Barcode presence detection error: {e}")
            return False
