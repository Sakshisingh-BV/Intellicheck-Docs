# app/validation/cross_validation.py
#
# Document Cross-Validation module.
#
# Consolidates all cross-document consistency checks into a single cohesive
# module with a unified API.  Each check function operates on a list of
# processed document dicts (as returned by DocumentProcessor) and returns
# a (is_consistent: bool, issues: list[str]) tuple.
#
# The top-level `cross_validate_documents` function runs every check and
# returns a single structured result dict.

import re
import logging
from typing import List, Tuple, Dict, Optional

from app.address_verification.extractor import AddressExtractor
from app.address_verification.matcher import AddressMatcher

logger = logging.getLogger(__name__)


# ── Document type categories ─────────────────────────────────────────────

ID_PROOF_TYPES = {"aadhaar_card", "pan_card", "passport"}
ADDRESS_PROOF_TYPES = {"aadhaar_card", "passport", "utility_bill", "bank_statement"}


# ── Internal helpers ─────────────────────────────────────────────────────

def _get_classification(doc: dict) -> dict:
    """Extract classification dict from a processed document."""
    return doc.get("classification", {})


def _get_fields(doc: dict) -> dict:
    """Extract extracted_fields dict from a processed document."""
    return _get_classification(doc).get("extracted_fields", {})


def _get_doc_type(doc: dict) -> str:
    """Extract document_type string from a processed document."""
    return _get_classification(doc).get("document_type", "unknown")


def _normalize_name(name: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    if not name:
        return ""
    return re.sub(r'\s+', ' ', name.strip().lower())


# Fields that carry a name value, keyed by document type
_NAME_FIELDS = {
    "pan_card": ["name", "father_name"],
    "passport": ["given_name", "surname"],
}

_DOB_FIELD = "date_of_birth"

# Fields that carry a document ID number, keyed by document type
_ID_NUMBER_FIELDS = {
    "aadhaar_card": "aadhaar_number",
    "pan_card": "pan_number",
    "passport": "passport_number",
}


# ── Individual check functions ───────────────────────────────────────────

def check_name_consistency(docs: List[dict]) -> Tuple[bool, List[str]]:
    """
    Check name consistency across documents.

    Compares normalised name strings across all documents that expose a
    name field.  If fewer than 2 documents have names, returns True
    (nothing to compare).

    Returns:
        (consistent: bool, mismatches: list[str])
    """
    names = []
    for doc in docs:
        doc_type = _get_doc_type(doc)
        fields = _get_fields(doc)

        name_keys = _NAME_FIELDS.get(doc_type, [])
        for key in name_keys:
            val = fields.get(key)
            if val:
                names.append((doc_type, key, _normalize_name(val)))
                break

        if not name_keys:
            val = fields.get("name")
            if val:
                names.append((doc_type, "name", _normalize_name(val)))

    if len(names) < 2:
        return True, []

    ref_type, _, ref_name = names[0]
    mismatches = []
    for doc_type, _, name in names[1:]:
        if name != ref_name:
            mismatches.append(
                f"Name mismatch: {ref_type}='{ref_name}' vs {doc_type}='{name}'"
            )

    return len(mismatches) == 0, mismatches


def check_dob_consistency(docs: List[dict]) -> Tuple[bool, List[str]]:
    """
    Check date-of-birth consistency across documents.

    Normalises date separators before comparing.

    Returns:
        (consistent: bool, mismatches: list[str])
    """
    dobs = []
    for doc in docs:
        doc_type = _get_doc_type(doc)
        fields = _get_fields(doc)
        dob = fields.get(_DOB_FIELD)
        if dob:
            dob_norm = re.sub(r'[\-\.]', '/', dob.strip())
            dobs.append((doc_type, dob_norm))

    if len(dobs) < 2:
        return True, []

    ref_type, ref_dob = dobs[0]
    mismatches = []
    for doc_type, dob in dobs[1:]:
        if dob != ref_dob:
            mismatches.append(
                f"DOB mismatch: {ref_type}='{ref_dob}' vs {doc_type}='{dob}'"
            )

    return len(mismatches) == 0, mismatches


def check_address_consistency(docs: List[dict]) -> Tuple[bool, List[str]]:
    """
    Check address consistency across documents using AddressMatcher.

    Extracts addresses from OCR text, then compares all pairs.

    Returns:
        (consistent: bool, issues: list[str])
    """
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
            if match_result.get("status") == "NO_MATCH":
                issues.append(
                    f"Address mismatch: {type_a} vs {type_b} — "
                    f"{match_result.get('reason', '')}"
                )

    return len(issues) == 0, issues


def check_document_id_match(docs: List[dict]) -> Tuple[bool, List[str]]:
    """
    Cross-validate document ID numbers across documents.

    For each ID number type (aadhaar, PAN, passport), check if the same
    number appears consistently when multiple documents reference it.

    For example, if an Aadhaar card has aadhaar_number "2345 6789 0123"
    and a bank statement also references aadhaar_number "2345 6789 0124",
    this flags a mismatch.

    Returns:
        (consistent: bool, mismatches: list[str])
    """
    # Collect all ID numbers keyed by field name
    id_map: Dict[str, List[Tuple[str, str]]] = {}

    for doc in docs:
        doc_type = _get_doc_type(doc)
        fields = _get_fields(doc)

        for dt, field_name in _ID_NUMBER_FIELDS.items():
            raw_value = fields.get(field_name)
            if raw_value:
                # Normalise: strip spaces, hyphens, uppercase
                normalised = re.sub(r'[\s\-]', '', str(raw_value).strip().upper())
                if normalised:
                    id_map.setdefault(field_name, []).append(
                        (doc_type, normalised)
                    )

    mismatches = []
    for field_name, entries in id_map.items():
        if len(entries) < 2:
            continue

        ref_type, ref_val = entries[0]
        for doc_type, val in entries[1:]:
            if val != ref_val:
                mismatches.append(
                    f"{field_name} mismatch: {ref_type}='{ref_val}' "
                    f"vs {doc_type}='{val}'"
                )

    return len(mismatches) == 0, mismatches


# ── Unified cross-validation API ─────────────────────────────────────────

def cross_validate_documents(docs: List[dict]) -> Dict:
    """
    Run all cross-document consistency checks and return a unified result.

    Checks performed:
        1. Name consistency
        2. DOB consistency
        3. Address consistency
        4. Document ID number consistency

    Args:
        docs: List of processed document dicts (from DocumentProcessor).

    Returns:
        {
            "is_consistent": bool,
            "checks": {
                "name":       {"consistent": bool, "issues": list[str]},
                "dob":        {"consistent": bool, "issues": list[str]},
                "address":    {"consistent": bool, "issues": list[str]},
                "document_id": {"consistent": bool, "issues": list[str]},
            },
            "all_issues": list[str],
        }
    """
    name_ok, name_issues = check_name_consistency(docs)
    dob_ok, dob_issues = check_dob_consistency(docs)
    addr_ok, addr_issues = check_address_consistency(docs)
    id_ok, id_issues = check_document_id_match(docs)

    all_issues = name_issues + dob_issues + addr_issues + id_issues

    return {
        "is_consistent": name_ok and dob_ok and addr_ok and id_ok,
        "checks": {
            "name": {"consistent": name_ok, "issues": name_issues},
            "dob": {"consistent": dob_ok, "issues": dob_issues},
            "address": {"consistent": addr_ok, "issues": addr_issues},
            "document_id": {"consistent": id_ok, "issues": id_issues},
        },
        "all_issues": all_issues,
    }
