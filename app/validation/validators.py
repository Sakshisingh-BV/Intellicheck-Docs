# app/validation/validators.py
#
# Field-level validators for Indian identity and address documents.
# Each function takes a string, returns (is_valid: bool, reason: str).
# No external dependencies — pure regex + arithmetic.

import re
from datetime import datetime


# ── Verhoeff checksum tables (for Aadhaar validation) ─────────────────────

_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def _verhoeff_checksum(number: str) -> bool:
    """Validate Verhoeff checksum. Returns True if valid."""
    c = 0
    for i, digit in enumerate(reversed(number)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(digit)]]
    return c == 0


# ── Validators ────────────────────────────────────────────────────────────

def validate_pan(pan: str) -> tuple:
    """
    Validate Indian PAN (Permanent Account Number).
    Format: ABCDE1234F — 5 letters, 4 digits, 1 letter.
    4th character encodes holder type (C=Company, P=Person, etc.).
    """
    if not pan:
        return False, "PAN is empty"

    pan = pan.strip().upper()

    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
        return False, f"Invalid PAN format: {pan}"

    valid_4th = set("ABCFGHLJPT")
    if pan[3] not in valid_4th:
        return False, f"Invalid PAN holder type: {pan[3]}"

    return True, ""


def validate_aadhaar(uid: str) -> tuple:
    """
    Validate Indian Aadhaar number.
    12 digits, cannot start with 0 or 1, Verhoeff checksum on last digit.
    """
    if not uid:
        return False, "Aadhaar is empty"

    # Strip spaces and hyphens (format: 1234 5678 9012)
    uid = re.sub(r'[\s\-]', '', uid.strip())

    if not re.match(r'^\d{12}$', uid):
        return False, f"Aadhaar must be 12 digits, got: {uid}"

    if uid[0] in ('0', '1'):
        return False, "Aadhaar cannot start with 0 or 1"

    if not _verhoeff_checksum(uid):
        return False, "Aadhaar checksum invalid"

    return True, ""


def validate_passport(num: str) -> tuple:
    """
    Validate Indian passport number.
    Format: 1 uppercase letter followed by 7 digits (e.g., L1234567).
    First letter is typically J, K, L, M, N, P, R, S, T, U, V, W, X, Y, Z.
    """
    if not num:
        return False, "Passport number is empty"

    num = num.strip().upper()

    if not re.match(r'^[A-Z]\d{7}$', num):
        return False, f"Invalid passport format: {num}"

    return True, ""


def validate_pincode(pin: str) -> tuple:
    """
    Validate Indian pincode.
    6 digits, first digit 1-9.
    """
    if not pin:
        return False, "Pincode is empty"

    pin = re.sub(r'\s', '', pin.strip())

    if not re.match(r'^[1-9]\d{5}$', pin):
        return False, f"Invalid pincode: {pin}"

    return True, ""


def validate_date(date_str: str) -> tuple:
    """
    Validate date string.
    Accepts: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY.
    Must not be in the future.
    """
    if not date_str:
        return False, "Date is empty"

    date_str = date_str.strip()

    # Normalize separators
    normalized = re.sub(r'[\-\.]', '/', date_str)

    try:
        parsed = datetime.strptime(normalized, "%d/%m/%Y")
    except ValueError:
        return False, f"Cannot parse date: {date_str}"

    if parsed > datetime.now():
        return False, f"Date is in the future: {date_str}"

    return True, ""


def validate_ifsc(code: str) -> tuple:
    """
    Validate IFSC code.
    Format: 4 letters + 0 + 6 alphanumeric (e.g., SBIN0001234).
    """
    if not code:
        return False, "IFSC code is empty"

    code = code.strip().upper()

    if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', code):
        return False, f"Invalid IFSC format: {code}"

    return True, ""


# ── Helper: validate all extracted fields for a document type ─────────────

# Map: document_type → { field_name: validator_function }
_FIELD_VALIDATORS = {
    "pan_card": {
        "pan_number": validate_pan,
        "date_of_birth": validate_date,
    },
    "aadhaar_card": {
        "aadhaar_number": validate_aadhaar,
        "date_of_birth": validate_date,
        "pincode": validate_pincode,
    },
    "passport": {
        "passport_number": validate_passport,
        "date_of_birth": validate_date,
        "date_of_issue": validate_date,
        "date_of_expiry": validate_date,
    },
    "bank_statement": {
        "ifsc_code": validate_ifsc,
    },
    "utility_bill": {
        "bill_date": validate_date,
        "due_date": validate_date,
    },
}


def validate_extracted_fields(doc_type: str, fields: dict) -> dict:
    """
    Validate all extracted fields for a given document type.

    Args:
        doc_type: Classification type name (e.g. "pan_card", "aadhaar_card").
        fields: Dict of field_name → value from ClassificationResult.extracted_fields.

    Returns:
        Dict with:
            valid: bool — True if all validated fields pass.
            results: dict of field_name → {is_valid, reason}.
    """
    validators = _FIELD_VALIDATORS.get(doc_type, {})
    results = {}
    all_valid = True

    for field_name, value in fields.items():
        validator_fn = validators.get(field_name)
        if validator_fn:
            is_valid, reason = validator_fn(value)
            results[field_name] = {"is_valid": is_valid, "reason": reason}
            if not is_valid:
                all_valid = False
        # Fields without a validator are skipped (no opinion = no failure)

    return {"valid": all_valid, "results": results}
