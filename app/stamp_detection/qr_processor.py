# app/stamp_detection/qr_processor.py
#
# Barcode detection and decoding for e-stamp documents.
#
# SHCIL e-stamp certificates use Data Matrix barcodes (confirmed by visual
# inspection of sample certificates). Generic documents may use QR codes.
#
# Decoder priority:
#   1. pylibdmtx          — Data Matrix decoder        (PRIMARY: SHCIL e-stamps)
#   2. pyzbar             — ZBar multi-format decoder  (FALLBACK: QR + DataMatrix)
#   3. cv2.QRCodeDetector — OpenCV QR-only decoder     (FALLBACK: genuine QR docs)
#
# Preprocessing pipeline (per-crop, in order of increasing cost):
#   Level 0: Raw crop             → decode
#   Level 1: Grayscale + Otsu     → decode
#   Level 2: CLAHE + 2× upscale   → decode
#   Level 3: Sharpen + CLAHE + 2× → decode
#
# detector.py calls qr_processor.process(image, is_likely_estamp) as the
# single entry point; the return dict is unchanged for API compatibility.

import cv2
import numpy as np
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional decoders — fail gracefully if not installed
# ---------------------------------------------------------------------------

try:
    from pylibdmtx.pylibdmtx import decode as _dmtx_decode
    HAS_DMTX = True
    logger.info("pylibdmtx available — Data Matrix decoding enabled (primary)")
except ImportError:
    HAS_DMTX = False
    logger.warning(
        "pylibdmtx not installed — Data Matrix decoding disabled. "
        "Install with: pip install pylibdmtx"
    )

try:
    import pyzbar.pyzbar as pyzbar
    HAS_PYZBAR = True
    logger.info("pyzbar available — multi-format barcode fallback enabled")
except ImportError:
    HAS_PYZBAR = False
    logger.warning("pyzbar not installed — multi-format barcode fallback disabled")


class QRProcessor:
    """
    Barcode detection and decoding for e-stamp documents.

    SHCIL e-stamp certificates use Data Matrix barcodes. Older/generic
    documents may use QR codes. This processor tries the correct decoder
    first, with minimal preprocessing, before escalating.

    Decoder priority (fastest/most targeted first):
        1. pylibdmtx  — Data Matrix (primary: SHCIL e-stamps)
        2. pyzbar     — ZBar multi-format (QR, DataMatrix, Code128, …)
        3. cv2        — OpenCV QRCodeDetector (QR-only fallback)

    Preprocessing levels (applied to each crop region in sequence):
        0: Raw image
        1: Grayscale + Otsu binarization
        2: CLAHE contrast enhancement + 2× upscale
        3: Sharpen + CLAHE + 2× upscale

    Usage:
        qr = QRProcessor()
        result = qr.process(image, is_likely_estamp=True)
        # → {"qr_present": True, "qr_decoded": True,
        #    "qr_data": "...", "decode_method": "dmtx_clahe2x_top_strip"}
    """

    # Crop regions: (y_start_ratio, y_end_ratio, x_start_ratio, x_end_ratio, label)
    #
    # SHCIL e-stamp barcodes (Data Matrix) are typically in the mid-left
    # zone (~55-80% from top). Older/simpler e-stamps put the QR in the
    # top or bottom strip. We cover all positions, most-likely first.
    QR_CROP_REGIONS = [
        (0.45, 0.85, 0.0,  0.40, "mid_left"),       # ← SHCIL e-stamps (stamp1, estamp2)
        (0.45, 0.85, 0.0,  1.0,  "mid_strip"),       # Wide mid band (catch any x position)
        (0.0,  0.30, 0.0,  0.40, "top_left"),        # Top-left corner
        (0.70, 1.0,  0.0,  0.40, "bottom_left"),     # Bottom-left corner
        (0.0,  0.30, 0.0,  1.0,  "top_strip"),       # Full top 30%
        (0.70, 1.0,  0.0,  1.0,  "bottom_strip"),    # Full bottom 30%
        (0.0,  0.30, 0.60, 1.0,  "top_right"),       # Top-right corner
        (0.70, 1.0,  0.60, 1.0,  "bottom_right"),    # Bottom-right corner
    ]

    # -----------------------------------------------------------------------
    # Public API (unchanged for detector.py compatibility)
    # -----------------------------------------------------------------------

    def process(self, image: np.ndarray, is_likely_estamp: bool = False) -> Dict:
        """
        Full barcode pipeline entry point.

        Args:
            image:             Full document image (BGR or grayscale).
            is_likely_estamp:  True when OCR text suggests an e-stamp document.
                               Triggers the region-crop + preprocessing pipeline
                               when the quick full-image decode fails.

        Returns:
            {
                "qr_present":    bool,        # visual presence detected
                "qr_decoded":    bool,        # payload successfully decoded
                "qr_data":       str | None,  # decoded payload string
                "decode_method": str | None,  # which step succeeded
            }
        """
        result: Dict = {
            "qr_present": False,
            "qr_decoded": False,
            "qr_data":    None,
            "decode_method": None,
        }

        # ------------------------------------------------------------------
        # Step 1: Quick decode on full image — no preprocessing
        # ------------------------------------------------------------------
        data, method = self._decode_barcode(image, "full_image")
        if data:
            result.update(
                qr_present=True,
                qr_decoded=True,
                qr_data=data,
                decode_method=method,
            )
            logger.info(f"Barcode decoded on first attempt: method={method}")
            return result

        # ------------------------------------------------------------------
        # Step 2: Visual presence check (informs logging; does not gate decode)
        # ------------------------------------------------------------------
        barcode_present = self._detect_barcode_presence(image)
        result["qr_present"] = barcode_present

        # ------------------------------------------------------------------
        # Step 3: Region-crop + preprocessing pipeline
        #         — only when e-stamp is likely OR barcode visually present
        # ------------------------------------------------------------------
        if not (is_likely_estamp or barcode_present):
            logger.debug(
                "Barcode enhanced pipeline skipped "
                "(not e-stamp, no barcode presence detected)"
            )
            return result

        logger.info(
            f"Triggering barcode enhanced pipeline "
            f"(is_likely_estamp={is_likely_estamp}, "
            f"barcode_present={barcode_present})"
        )

        h, w = image.shape[:2]
        crops = self._crop_regions(image)

        for crop, region_label in crops:
            decoded = self._try_progressive_decode(crop, region_label)
            if decoded:
                data, method = decoded
                result.update(
                    qr_present=True,
                    qr_decoded=True,
                    qr_data=data,
                    decode_method=method,
                )
                logger.info(f"Barcode decoded via enhanced pipeline: method={method}")
                return result

        # Diagnose failure cause
        min_crop_dim = min(
            (min(c.shape[:2]) for c, _ in crops), default=0
        )
        if barcode_present and min_crop_dim < 150:
            logger.warning(
                f"Barcode decode failed — likely cause: source image too low-resolution "
                f"(image={w}×{h}px, smallest crop={min_crop_dim}px). "
                f"Recommend scanning at 300+ DPI."
            )
        else:
            logger.info("Barcode enhanced pipeline exhausted — decode failed")

        return result

    # -----------------------------------------------------------------------
    # Progressive Decode Pipeline (per crop)
    # -----------------------------------------------------------------------

    def _try_progressive_decode(
        self, crop: np.ndarray, region_label: str
    ) -> Optional[Tuple[str, str]]:
        """
        Try progressively more expensive preprocessing on a single crop.

        Four levels — stops at the first successful decode.

        Returns:
            (decoded_string, method_label) on success, or None.
        """
        # Level 0: Raw crop
        data, method = self._decode_barcode(crop, f"raw_{region_label}")
        if data:
            return data, method

        # Level 1: Grayscale + Otsu binarization
        binary = self._to_binary(crop)
        data, method = self._decode_barcode(binary, f"binary_{region_label}")
        if data:
            return data, method

        # Level 2: CLAHE contrast enhancement + 2× upscale
        enhanced = self._apply_clahe(crop)
        upscaled = self._upscale(enhanced, factor=2)
        data, method = self._decode_barcode(upscaled, f"clahe2x_{region_label}")
        if data:
            return data, method

        # Level 3: Sharpen → CLAHE → 2× upscale
        # Useful for watermarked/noisy e-stamps where edges are degraded.
        sharpened = self._sharpen(crop)
        sharp_enhanced = self._apply_clahe(sharpened)
        sharp_upscaled = self._upscale(sharp_enhanced, factor=2)
        data, method = self._decode_barcode(sharp_upscaled, f"sharp_clahe2x_{region_label}")
        if data:
            return data, method

        return None

    # -----------------------------------------------------------------------
    # Barcode Decoding — all three decoders in priority order
    # -----------------------------------------------------------------------

    def _decode_barcode(
        self, image: np.ndarray, step_label: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Attempt to decode a barcode from image using all available decoders.

        Decoder order:
            1. pylibdmtx  — Data Matrix (SHCIL e-stamps)
            2. pyzbar     — ZBar multi-format (QR, DataMatrix, Code128, …)
            3. cv2        — OpenCV QRCodeDetector (QR only)

        Args:
            image:      BGR or grayscale numpy array.
            step_label: Label prefix used to build the decode_method string.

        Returns:
            (decoded_string, "decoder_step_label") on success,
            (None, None) on failure.
        """
        # Ensure image is in a usable format
        img_for_decode = self._ensure_uint8(image)

        # --- Decoder 1: pylibdmtx (Data Matrix) ---
        if HAS_DMTX:
            try:
                # pylibdmtx works best with grayscale uint8
                gray = (
                    cv2.cvtColor(img_for_decode, cv2.COLOR_BGR2GRAY)
                    if len(img_for_decode.shape) == 3
                    else img_for_decode
                )
                # Use generous timeout for scanned/compressed documents;
                # 500ms is too tight for degraded Data Matrix codes.
                results = _dmtx_decode(gray, timeout=3000)
                if results:
                    payload = results[0].data.decode("utf-8", errors="replace").strip()
                    if payload:
                        logger.debug(f"pylibdmtx decoded [{step_label}]: {payload[:80]}")
                        return payload, f"dmtx_{step_label}"
            except Exception as e:
                logger.debug(f"pylibdmtx error [{step_label}]: {e}")

        # --- Decoder 2: pyzbar (ZBar multi-format) ---
        if HAS_PYZBAR:
            try:
                decoded_list = pyzbar.decode(img_for_decode)
                if decoded_list:
                    payload = decoded_list[0].data.decode("utf-8", errors="replace").strip()
                    if payload:
                        btype = decoded_list[0].type
                        logger.debug(
                            f"pyzbar decoded [{step_label}] type={btype}: {payload[:80]}"
                        )
                        return payload, f"pyzbar_{step_label}"
            except Exception as e:
                logger.debug(f"pyzbar error [{step_label}]: {e}")

        # --- Decoder 3: OpenCV QRCodeDetector (QR only) ---
        try:
            detector = cv2.QRCodeDetector()
            val, pts, _ = detector.detectAndDecode(img_for_decode)
            if val:
                logger.debug(f"OpenCV QR decoded [{step_label}]: {val[:80]}")
                return val, f"opencv_qr_{step_label}"
        except Exception as e:
            logger.debug(f"OpenCV QR error [{step_label}]: {e}")

        return None, None

    # -----------------------------------------------------------------------
    # Region Cropping
    # -----------------------------------------------------------------------

    def _crop_regions(
        self, image: np.ndarray
    ) -> List[Tuple[np.ndarray, str]]:
        """
        Crop likely barcode regions from the document image.

        Returns:
            List of (cropped_image, region_label) tuples,
            skipping any degenerate (zero-size) crops.
        """
        h, w = image.shape[:2]
        crops = []
        for y1_r, y2_r, x1_r, x2_r, label in self.QR_CROP_REGIONS:
            y1, y2 = int(y1_r * h), int(y2_r * h)
            x1, x2 = int(x1_r * w), int(x2_r * w)
            crop = image[y1:y2, x1:x2]
            if crop.size > 0:
                crops.append((crop, label))
        return crops

    # -----------------------------------------------------------------------
    # Preprocessing Helpers
    # -----------------------------------------------------------------------

    def _ensure_uint8(self, image: np.ndarray) -> np.ndarray:
        """Ensure image is uint8; clip and convert if needed."""
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        return image

    def _to_binary(self, image: np.ndarray) -> np.ndarray:
        """Grayscale + Otsu binarization."""
        gray = (
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if len(image.shape) == 3
            else image
        )
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return binary

    def _apply_clahe(self, image: np.ndarray) -> np.ndarray:
        """CLAHE contrast-limited adaptive histogram equalization."""
        gray = (
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if len(image.shape) == 3
            else image
        )
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """Sharpen with a 3×3 high-pass kernel to recover barcode edges."""
        gray = (
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if len(image.shape) == 3
            else image
        )
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        return cv2.filter2D(gray, -1, kernel)

    def _upscale(self, image: np.ndarray, factor: int = 2) -> np.ndarray:
        """Upscale by factor using cubic interpolation."""
        h, w = image.shape[:2]
        return cv2.resize(
            image, (w * factor, h * factor), interpolation=cv2.INTER_CUBIC
        )

    # -----------------------------------------------------------------------
    # Barcode Visual Presence Detection
    # -----------------------------------------------------------------------

    def _detect_barcode_presence(self, image: np.ndarray) -> bool:
        """
        Lightweight check for a 2-D barcode (Data Matrix or QR) anywhere
        in the image using contour analysis.

        Data Matrix indicators:
            - Dense square region with a solid L-shaped border (left + bottom
              columns all-black; top + right rows alternating).

        QR code indicators:
            - Three nested-square "finder patterns" in corners.

        Both cases produce contours with child structures.
        Returns True if ≥ 2 candidate barcode-pattern contours are found.
        """
        try:
            gray = (
                cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                if len(image.shape) == 3
                else image
            )

            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=51,
                C=10,
            )

            contours, hierarchy = cv2.findContours(
                binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )
            if hierarchy is None or len(contours) == 0:
                return False

            hierarchy = hierarchy[0]  # shape: (N, 4) — [next, prev, child, parent]
            candidates = 0

            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area < 40:
                    continue  # skip noise

                x, y, w, h = cv2.boundingRect(contour)
                if h == 0 or w == 0:
                    continue

                aspect = float(w) / float(h)
                if not (0.4 <= aspect <= 2.5):
                    continue  # barcode regions are roughly square or rectangular

                # Must have child contours (nested structure present in both
                # QR finder patterns and Data Matrix border encoding)
                if hierarchy[i][2] == -1:
                    continue

                candidates += 1

            is_present = candidates >= 2
            logger.debug(
                f"Barcode presence: {candidates} candidate regions → "
                f"{'detected' if is_present else 'not found'}"
            )
            return is_present

        except Exception as e:
            logger.debug(f"Barcode presence detection error: {e}")
            return False
