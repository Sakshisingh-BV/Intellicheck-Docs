# app/validation/proof_check.py
#
# Cross-document proof checking for ID & Address verification.
# Operates on processed document dicts (output of DocumentProcessor).
#
# Delegates cross-document consistency checks to cross_validation module
# and field-level validation to validators module.

import logging
from .validators import validate_extracted_fields
from .cross_validation import (
    cross_validate_documents,
    check_name_consistency,
    check_dob_consistency,
    check_address_consistency,
    check_document_id_match,
    ID_PROOF_TYPES,
    ADDRESS_PROOF_TYPES,
    _get_classification,
    _get_fields,
    _get_doc_type,
)

logger = logging.getLogger(__name__)


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


# Backward-compatible aliases — delegate to cross_validation module
check_name_match = check_name_consistency
check_dob_match = check_dob_consistency
check_address_match = check_address_consistency


def generate_status(docs: list) -> dict:
    """
    Run full proof check and produce a PASS / REVIEW / REJECT verdict.

    Args:
        docs: List of processed document dicts (from DocumentProcessor).
              Each dict should have: classification (with document_type,
              extracted_fields), ocr_result (with text).

    Returns:
        Dict with:
            status:            "PASS" | "REVIEW" | "REJECT"
            reasons:           list[str] — human-readable explanation
            proofs:            {met: bool, missing: list}
            field_validation:  list of per-doc validation results
            name_check:        {consistent: bool, mismatches: list}
            dob_check:         {consistent: bool, mismatches: list}
            address_check:     {consistent: bool, issues: list}
            document_id_check: {consistent: bool, mismatches: list}
            cross_validation:  full cross_validate_documents result
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
                for fname, fresult in validation["results"].items():
                    if not fresult["is_valid"]:
                        reasons.append(
                            f"{doc_type}.{fname}: {fresult['reason']}"
                        )

    # 3. Cross-document validation (delegated to cross_validation module)
    cross_result = cross_validate_documents(docs)

    name_ok = cross_result["checks"]["name"]["consistent"]
    name_mismatches = cross_result["checks"]["name"]["issues"]
    if not name_ok:
        reasons.extend(name_mismatches)

    dob_ok = cross_result["checks"]["dob"]["consistent"]
    dob_mismatches = cross_result["checks"]["dob"]["issues"]
    if not dob_ok:
        reasons.extend(dob_mismatches)

    addr_ok = cross_result["checks"]["address"]["consistent"]
    addr_issues = cross_result["checks"]["address"]["issues"]
    if not addr_ok:
        reasons.extend(addr_issues)

    id_ok = cross_result["checks"]["document_id"]["consistent"]
    id_mismatches = cross_result["checks"]["document_id"]["issues"]
    if not id_ok:
        reasons.extend(id_mismatches)

    # 4. Check for low-confidence classifications
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
    elif not name_ok or not dob_ok or not addr_ok or not id_ok or low_confidence:
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
        "document_id_check": {"consistent": id_ok, "mismatches": id_mismatches},
        "cross_validation": cross_result,
    }
