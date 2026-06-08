# app/validation/proof_check.py
#
# Cross-document proof checking for ID & Address verification.
# Operates on processed document dicts (output of DocumentProcessor).
# Reuses existing classification results and address verification module.

import re
import logging
from .validators import validate_extracted_fields
from app.address_verification.extractor import AddressExtractor
from app.address_verification.matcher import AddressMatcher

logger = logging.getLogger(__name__)


# ── Document type categorisation ──────────────────────────────────────────

ID_PROOF_TYPES = {"aadhaar_card", "pan_card", "passport"}
ADDRESS_PROOF_TYPES = {"aadhaar_card", "passport", "utility_bill", "bank_statement"}

# Fields that carry a name value, by document type
_NAME_FIELDS = {
    "pan_card": ["name", "father_name"],
    "passport": ["given_name", "surname"],
}

# Fields that carry DOB
_DOB_FIELD = "date_of_birth"


# ── Helpers ───────────────────────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    if not name:
        return ""
    return re.sub(r'\s+', ' ', name.strip().lower())


def _get_classification(doc: dict) -> dict:
    """Extract classification dict from a processed document."""
    return doc.get("classification", {})


def _get_fields(doc: dict) -> dict:
    """Extract extracted_fields dict from a processed document."""
    return _get_classification(doc).get("extracted_fields", {})


def _get_doc_type(doc: dict) -> str:
    """Extract document_type string from a processed document."""
    return _get_classification(doc).get("document_type", "unknown")


# ── Public API ────────────────────────────────────────────────────────────

def check_required_proofs(docs: list) -> tuple:
    """
    Check whether at least 1 ID proof and 1 address proof are present.

    Args:
        docs: List of processed document dicts (from DocumentProcessor).

    Returns:
        (met: bool, missing: list[str])
    """
    found_id = False
    found_address = False

    for doc in docs:
        doc_type = _get_doc_type(doc)
        if doc_type in ID_PROOF_TYPES:
            found_id = True
        if doc_type in ADDRESS_PROOF_TYPES:
            found_address = True

    missing = []
    if not found_id:
        missing.append("ID proof (aadhaar_card / pan_card / passport)")
    if not found_address:
        missing.append("Address proof (aadhaar_card / passport / utility_bill / bank_statement)")

    return len(missing) == 0, missing


def check_name_match(docs: list) -> tuple:
    """
    Check name consistency across documents.
    Uses simple normalized string comparison (exact after normalisation).

    Only compares documents that have an extractable name field.
    If fewer than 2 documents have names, returns True (nothing to compare).

    Args:
        docs: List of processed document dicts.

    Returns:
        (consistent: bool, mismatches: list[str])
    """
    # Collect (doc_type, name) pairs
    names = []
    for doc in docs:
        doc_type = _get_doc_type(doc)
        fields = _get_fields(doc)

        # Try known name fields for this doc type
        name_keys = _NAME_FIELDS.get(doc_type, [])
        for key in name_keys:
            val = fields.get(key)
            if val:
                names.append((doc_type, key, _normalize_name(val)))
                break  # one name per document is enough

        # Fallback: generic "name" field
        if not name_keys:
            val = fields.get("name")
            if val:
                names.append((doc_type, "name", _normalize_name(val)))

    if len(names) < 2:
        return True, []

    # Compare all pairs against the first
    reference_type, _, reference_name = names[0]
    mismatches = []
    for doc_type, field_key, name in names[1:]:
        if name != reference_name:
            mismatches.append(
                f"Name mismatch: {reference_type}='{reference_name}' vs {doc_type}='{name}'"
            )

    return len(mismatches) == 0, mismatches


def check_dob_match(docs: list) -> tuple:
    """
    Check DOB consistency across documents. Exact match after normalisation.

    Args:
        docs: List of processed document dicts.

    Returns:
        (consistent: bool, mismatches: list[str])
    """
    dobs = []
    for doc in docs:
        doc_type = _get_doc_type(doc)
        fields = _get_fields(doc)
        dob = fields.get(_DOB_FIELD)
        if dob:
            # Normalise separators for comparison
            dob_norm = re.sub(r'[\-\.]', '/', dob.strip())
            dobs.append((doc_type, dob_norm))

    if len(dobs) < 2:
        return True, []

    reference_type, reference_dob = dobs[0]
    mismatches = []
    for doc_type, dob in dobs[1:]:
        if dob != reference_dob:
            mismatches.append(
                f"DOB mismatch: {reference_type}='{reference_dob}' vs {doc_type}='{dob}'"
            )

    return len(mismatches) == 0, mismatches


def check_address_match(docs: list) -> tuple:
    """
    Check address consistency across documents using existing AddressMatcher.
    Extracts addresses from OCR text, compares all pairs.

    Args:
        docs: List of processed document dicts.

    Returns:
        (consistent: bool, issues: list[str])
    """
    # Extract addresses from docs that have OCR text
    addr_docs = []
    for doc in docs:
        doc_type = _get_doc_type(doc)
        ocr_text = doc.get("ocr_result", {}).get("text", "")
        if not ocr_text:
            continue

        addr = AddressExtractor.extract_from_text(ocr_text)
        if addr:
            addr_docs.append((doc_type, addr))

    if len(addr_docs) < 2:
        return True, []

    issues = []
    for i in range(len(addr_docs)):
        for j in range(i + 1, len(addr_docs)):
            type_a, addr_a = addr_docs[i]
            type_b, addr_b = addr_docs[j]
            match_result = AddressMatcher.compare(addr_a, addr_b)
            status = match_result.get("status", "NO_MATCH")
            if status == "NO_MATCH":
                issues.append(
                    f"Address mismatch: {type_a} vs {type_b} — {match_result.get('reason', '')}"
                )

    return len(issues) == 0, issues


def generate_status(docs: list) -> dict:
    """
    Run full proof check and produce a PASS / REVIEW / REJECT verdict.

    Args:
        docs: List of processed document dicts (from DocumentProcessor).
              Each dict should have: classification (with document_type,
              extracted_fields), ocr_result (with text).

    Returns:
        Dict with:
            status:           "PASS" | "REVIEW" | "REJECT"
            reasons:          list[str] — human-readable explanation
            proofs:           {met: bool, missing: list}
            field_validation: list of per-doc validation results
            name_check:       {consistent: bool, mismatches: list}
            dob_check:        {consistent: bool, mismatches: list}
            address_check:    {consistent: bool, issues: list}
    """
    reasons = []

    # 1. Required proofs
    proofs_met, proofs_missing = check_required_proofs(docs)
    if not proofs_met:
        reasons.append(f"Missing proofs: {', '.join(proofs_missing)}")

    # 2. Field validation per document
    field_validations = []
    any_field_invalid = False
    for doc in docs:
        doc_type = _get_doc_type(doc)
        fields = _get_fields(doc)
        if fields:
            validation = validate_extracted_fields(doc_type, fields)
            validation["doc_type"] = doc_type
            field_validations.append(validation)
            if not validation["valid"]:
                any_field_invalid = True
                # Collect specific failures
                for fname, fresult in validation["results"].items():
                    if not fresult["is_valid"]:
                        reasons.append(
                            f"{doc_type}.{fname}: {fresult['reason']}"
                        )

    # 3. Cross-document: name
    name_ok, name_mismatches = check_name_match(docs)
    if not name_ok:
        reasons.extend(name_mismatches)

    # 4. Cross-document: DOB
    dob_ok, dob_mismatches = check_dob_match(docs)
    if not dob_ok:
        reasons.extend(dob_mismatches)

    # 5. Cross-document: address
    addr_ok, addr_issues = check_address_match(docs)
    if not addr_ok:
        reasons.extend(addr_issues)

    # 6. Check for low-confidence classifications
    low_confidence = False
    for doc in docs:
        conf = _get_classification(doc).get("confidence", 0.0)
        doc_type = _get_doc_type(doc)
        if doc_type != "unknown" and conf < 0.3:
            low_confidence = True
            reasons.append(f"Low classification confidence for {doc_type}: {conf:.2f}")

    # ── Decision ──────────────────────────────────────────────────────────

    if not proofs_met or any_field_invalid:
        status = "REJECT"
    elif not name_ok or not dob_ok or not addr_ok or low_confidence:
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "status": status,
        "reasons": reasons,
        "proofs": {"met": proofs_met, "missing": proofs_missing},
        "field_validation": field_validations,
        "name_check": {"consistent": name_ok, "mismatches": name_mismatches},
        "dob_check": {"consistent": dob_ok, "mismatches": dob_mismatches},
        "address_check": {"consistent": addr_ok, "issues": addr_issues},
    }
