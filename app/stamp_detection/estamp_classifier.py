# app/stamp_detection/estamp_classifier.py
#
# E-Stamp document classification via weighted scoring.
#
# Extracted from detector.py — this module handles:
#   1. Full-page OCR with blur-aware retry
#   2. Weighted e-stamp scoring (context-aware)
#   3. Text field extraction (cert number, stamp duty, state, date)
#   4. QR vs certificate cross-validation
#
# The classifier is stateless beyond its injected dependencies
# (OCREngine, QRProcessor). It does NOT touch YOLO or anomaly detection.

import re
import logging
import numpy as np
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

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


class EStampClassifier:
    """
    E-Stamp document classifier using weighted keyword scoring.

    Architecture:
        Full-page OCR classifies the document type (document classification).
        Weighted scoring determines if the document is an e-stamp.
        Extracted fields (certificate_number, stamp_duty, state, date)
        are always returned for OCR debugging.

    Scoring weights:
        certificate_number = 40  (PRIMARY — sets context)
        stamp_duty         = 25  (SECONDARY — requires context)
        state              = 15  (SECONDARY — requires context)
        date               = 10  (SECONDARY — requires context)
        qr_present         =  2  (contour-based visual presence, weak signal)
        qr_decoded         =  5  (decoded payload — pylibdmtx/pyzbar/OpenCV, strong)
        threshold          = 50

    Context is established by certificate_number OR e-stamp keywords
    (e-Stamp, SHCIL, Certificate No., etc.). Without context,
    secondary fields do NOT contribute to the score.
    """

    # --- Weighted scoring configuration ---
    ESTAMP_WEIGHTS = {
        "certificate_number": 40,
        "stamp_duty": 25,
        "state": 15,
        "date": 10,
        "qr_present": 2,    # weak signal: contour-based visual presence
        "qr_decoded": 5,    # strong signal: decoded payload (pylibdmtx/pyzbar/OpenCV)
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

    def __init__(self, ocr_engine=None, qr_processor=None):
        """
        Initialise the e-stamp classifier.

        Args:
            ocr_engine: An initialised OCREngine instance (or None).
            qr_processor: An initialised QRProcessor instance (or None).
        """
        self.ocr_engine = ocr_engine
        self.qr_processor = qr_processor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, image: np.ndarray) -> Dict:
        """
        Classify whether an image is an e-stamp document.

        Returns:
            {
                "document_type": "e_stamp" | "non_e_stamp",
                "is_estamp_document": bool,
                "document_fields": {
                    "certificate_number": str | None,
                    "stamp_duty": str | None,
                    "state": str | None,
                    "date": str | None,
                    "qr_present": bool,
                    "qr_decoded": bool,
                    "qr_data": str | None,
                    "qr_certificate_match": bool | None,
                    "qr_certificate_number": str | None,
                    "estamp_score": int,
                    "estamp_threshold": int,
                    "scoring_breakdown": { ... },
                    "blur_score": float | None,
                    "blur_level": str,
                    "ocr_retried": bool,
                },
            }
        """
        try:
            # Step 1: Full-page OCR with blur-aware retry
            full_text, blur_info = self._run_full_page_ocr(image)

            # Step 2: QR detection + decoding
            has_estamp_indicators = (
                self._has_estamp_text_indicator(full_text)
                or bool(self._extract_cert_number(full_text))
            )

            if self.qr_processor is not None:
                qr_result = self.qr_processor.process(
                    image, is_likely_estamp=has_estamp_indicators
                )
                qr_present = qr_result["qr_present"]
                qr_decoded = qr_result["qr_decoded"]
                qr_data = qr_result["qr_data"]
            else:
                qr_present = False
                qr_decoded = False
                qr_data = None

            logger.info(
                f"Barcode detection: qr_present={qr_present}, "
                f"qr_decoded={qr_decoded}"
            )

            # Step 3: Weighted scoring
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

            # Step 4: QR vs certificate cross-validation
            qr_validation = self._validate_qr_vs_certificate(
                qr_data, estamp_details.get("certificate_number")
            )

            # Build document_fields
            document_fields = {
                "certificate_number": estamp_details.get("certificate_number"),
                "stamp_duty": estamp_details.get("stamp_duty_value"),
                "state": estamp_details.get("state"),
                "date": estamp_details.get("date"),
                "qr_present": qr_present,
                "qr_decoded": qr_decoded,
                "qr_data": qr_data,
                "qr_certificate_match": qr_validation.get("match"),
                "qr_certificate_number": qr_validation.get("qr_cert_number"),
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
            }

        except Exception as e:
            logger.error(f"E-stamp classification error: {e}")
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
                    "estamp_threshold": self.ESTAMP_THRESHOLD,
                    "scoring_breakdown": {},
                    "blur_score": None,
                    "blur_level": "unknown",
                    "ocr_retried": False,
                },
            }

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

        Weights (context-aware):
            certificate_number  = 40  (PRIMARY — establishes context)
            stamp_duty          = 25  (SECONDARY — requires context)
            state               = 15  (SECONDARY — requires context)
            date                = 10  (SECONDARY — requires context)
            qr_present          =  2  (weak signal, contour-based)
            qr_decoded          =  5  (strong signal, pyzbar decode)

        Context = certificate_number found OR e-stamp keyword detected.

        Returns:
            (score: int, details: dict)
        """
        score = 0
        breakdown = {}

        cert_number = self._extract_cert_number(full_text)
        has_text_indicator = self._has_estamp_text_indicator(full_text)
        has_estamp_context = bool(cert_number or has_text_indicator)

        # --- Certificate number (weight 40, PRIMARY) ---
        if cert_number:
            score += self.ESTAMP_WEIGHTS["certificate_number"]
            breakdown["certificate_number"] = {
                "found": True, "value": cert_number,
                "points": self.ESTAMP_WEIGHTS["certificate_number"]
            }
        else:
            breakdown["certificate_number"] = {"found": False, "points": 0}

        state = self._extract_state(full_text)
        # State no longer sets context — it is itself gated by context

        # --- State (weight 15, SECONDARY — only if e-stamp context) ---
        if state and has_estamp_context:
            score += self.ESTAMP_WEIGHTS["state"]
            breakdown["state"] = {
                "found": True, "value": state,
                "points": self.ESTAMP_WEIGHTS["state"],
                "awarded": "due to e-stamp context"
            }
        else:
            breakdown["state"] = {
                "found": bool(state),
                "value": state,
                "points": 0,
                "reason": "requires e-stamp context" if state else "not found"
            }

        # --- Stamp duty value (weight 25, SECONDARY - only if e-stamp context) ---
        stamp_value = self._extract_stamp_value(full_text)
        if stamp_value and has_estamp_context:
            score += self.ESTAMP_WEIGHTS["stamp_duty"]
            breakdown["stamp_duty"] = {
                "found": True, "value": stamp_value,
                "points": self.ESTAMP_WEIGHTS["stamp_duty"],
                "awarded": "due to e-stamp context"
            }
        else:
            breakdown["stamp_duty"] = {
                "found": bool(stamp_value),
                "value": stamp_value,
                "points": 0,
                "reason": "requires e-stamp context" if stamp_value else "not found"
            }

        # --- Date (weight 10, SECONDARY - only if e-stamp context) ---
        date = self._extract_date(full_text)
        if date and has_estamp_context:
            score += self.ESTAMP_WEIGHTS["date"]
            breakdown["date"] = {
                "found": True, "value": date,
                "points": self.ESTAMP_WEIGHTS["date"],
                "awarded": "due to e-stamp context"
            }
        else:
            breakdown["date"] = {
                "found": bool(date),
                "value": date,
                "points": 0,
                "reason": "requires e-stamp context" if date else "not found"
            }

        # --- QR presence (weight 2, weak signal) ---
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
            # Only surface secondary fields when e-stamp context exists;
            # raw extracted values are still in scoring_breakdown for debugging
            "stamp_duty_value": stamp_value if has_estamp_context else None,
            "state": state if has_estamp_context else None,
            "date": date if has_estamp_context else None,
            "has_estamp_context": has_estamp_context,
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
            r'IN-[A-Z]{2}\d{14,20}[A-Z]?',             # SHCIL format (with optional trailing letter like V, X)
            r'[A-Z]{2,3}-\d{6}-\d{6}',                  # State-date-serial
            r'[Cc]ertificate\s*(?:[Nn]o\.?|#)\s*[:.]?\s*([A-Z0-9\-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0) if match.lastindex is None else match.group(1)

        return None

    def _extract_stamp_value(self, text: str) -> Optional[str]:
        """Extract stamp duty value - handle multiple formats"""
        if not text:
            return None

        patterns = [
            # Format: "Stamp Duty Amount(Rs.) : 100"
            r'[Ss]tamp\s+[Dd]uty\s+(?:Amount)?\s*\(?Rs\.?\)?(?:\s*[:=])?\s*(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)',
            # Format: "Rs. 100" or "₹ 100" — require ≥2 digits to avoid day-of-month
            r'(?:Rs\.?|INR|₹)\s*(\d{2,5}(?:,\d{3})*(?:\.\d{2})?)',
            # Format: "Consideration Price ... 100"
            r'[Cc]onsideration\s+[Pp]rice.*?(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)',
            # Format: "100 only"
            r'(\d{1,5}(?:,\d{3})*)\s+[Oo]nly',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                logger.info(f"Stamp duty extracted: {value}")
                return value

        return None

    def _extract_state(self, text: str) -> Optional[str]:
        """Extract issuing state from e-stamp context."""
        if not text:
            return None

        state_names = "|".join(re.escape(state) for state in self.KNOWN_STATES)

        labeled_patterns = [
            rf'\bstate\s*(?:of)?\s*(?:issue|issuance|certificate)?\s*[:=\-]?\s*({state_names})\b',
            rf'\bissued\s+in\s+the\s+state\s+of\s+({state_names})\b',
            rf'\bgovernment\s+of\s+({state_names})\b',
            rf'\bgovernment\s+of\s+NCT\s+of\s+({state_names})\b',
        ]

        for pattern in labeled_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._canonical_state_name(match.group(1))

        if not self._has_estamp_text_indicator(text):
            return None

        text_lower = text.lower()
        for state in self.KNOWN_STATES:
            if state.lower() in text_lower:
                return state

        return None

    def _canonical_state_name(self, value: str) -> Optional[str]:
        """Return the configured state spelling for a matched state value."""
        value_lower = value.lower()
        for state in self.KNOWN_STATES:
            if state.lower() == value_lower:
                return state
        return None

    def _has_estamp_text_indicator(self, text: str) -> bool:
        """Detect document-level e-stamp wording without relying on amounts or dates."""
        if not text:
            return False

        patterns = [
            r'\be[\s\-]?stamp(?:ing|ed)?\b',
            r'\belectronic\s+stamp(?:ing)?\b',
            r'\bshcil\b',
            r'\bstock\s+holding\s+corporation\b',
            r'\bstock\s+holding\b',
            r'\bcertificate\s*(?:no\.?|number|#)\b',
            r'\bunique\s+(?:document|doc|identification)\s+(?:reference|number|no\.?)\b',
            r'\baccount\s+reference\b',
            r'\bcertificate\s+issued\s+date\b',
            r'\bstamp\s+duty\s+paid\s+by\b',
            r'\bfirst\s+party\b',
            r'\bsecond\s+party\b',
            r'\bdescription\s+of\s+document\b',
            r'\bwww\.shcilestamp\.com\b',
            r'\bconsideration\s+price\b',
            r'\bgovernment\s+of\s+NCT\b',
        ]

        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract issue date - handle multiple formats"""
        if not text:
            return None

        patterns = [
            # Format: "14-Dec-2023 05:54 PM"
            r'(\d{1,2})-([A-Za-z]{3})-(\d{4})',
            # Format: "14-12-2023"
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            # Format: "2023-12-14"
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',
            # Format: "14 December 2023"
            r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
            # Format with word "Date:"
            r'[Dd]ate\s*[:=]\s*(\d{1,2}[/-]?[A-Za-z0-9\-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                logger.info(f"Date extracted: {date_str}")
                return date_str

        return None

    # ------------------------------------------------------------------
    # QR vs Certificate Cross-Validation (informational only)
    # ------------------------------------------------------------------

    def _validate_qr_vs_certificate(
        self, qr_data: Optional[str], ocr_cert_number: Optional[str]
    ) -> Dict:
        """
        Compare certificate number from QR payload against OCR-extracted
        certificate number.

        This is informational validation only — it does NOT affect
        estamp scoring or document_type.

        Returns:
            {
                "match": True | False | None,
                    True  = both found and they match
                    False = both found but they differ
                    None  = one or both not available (comparison not possible)
                "qr_cert_number": str | None
            }
        """
        if not qr_data:
            return {"match": None, "qr_cert_number": None}

        # Try to extract a certificate number from the QR payload
        qr_cert = self._extract_cert_number(qr_data)

        # If regex didn't match, try URL/query-parameter extraction
        if not qr_cert:
            qr_cert = self._extract_cert_from_url(qr_data)

        if not qr_cert:
            logger.debug(
                "QR validation: could not extract certificate number from QR data"
            )
            return {"match": None, "qr_cert_number": None}

        if not ocr_cert_number:
            logger.debug(
                f"QR validation: QR cert={qr_cert}, but OCR cert not available"
            )
            return {"match": None, "qr_cert_number": qr_cert}

        # Normalise for comparison (strip whitespace, uppercase)
        qr_norm = qr_cert.strip().upper()
        ocr_norm = ocr_cert_number.strip().upper()

        is_match = qr_norm == ocr_norm

        logger.info(
            f"QR validation: qr_cert={qr_cert}, ocr_cert={ocr_cert_number}, "
            f"match={is_match}"
        )

        return {"match": is_match, "qr_cert_number": qr_cert}

    def _extract_cert_from_url(self, text: str) -> Optional[str]:
        """
        Extract certificate number from a URL query parameter.

        Handles common e-stamp verification URLs like:
            https://www.shcilestamp.com/verify?cert=IN-DL12854...
            https://estamp.gov.in/verify?certificate_number=MH-240101-123456
        """
        try:
            parsed = urlparse(text.strip())
            if not parsed.scheme or not parsed.netloc:
                return None

            params = parse_qs(parsed.query)

            # Common parameter names for certificate number
            param_names = [
                "cert", "certificate", "certificate_number",
                "certno", "cert_no", "certificateno",
                "id", "ref", "refno",
            ]

            for name in param_names:
                values = params.get(name)
                if values:
                    # Try to validate the value looks like a cert number
                    candidate = values[0]
                    verified = self._extract_cert_number(candidate)
                    if verified:
                        return verified
                    # If it doesn't match known patterns but is alphanumeric,
                    # return it as-is (some states use non-standard formats)
                    if re.match(r'^[A-Z0-9\-]{6,}$', candidate, re.IGNORECASE):
                        return candidate

            # Fallback: try extracting cert number from full URL string
            # (some URLs embed the cert number in the path)
            return self._extract_cert_number(parsed.path)

        except Exception as e:
            logger.debug(f"URL cert extraction error: {e}")
            return None
