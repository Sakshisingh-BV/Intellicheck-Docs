# tests/test_cross_validation.py
#
# Unit tests for app.validation.cross_validation module.

import pytest
from app.validation.cross_validation import (
    check_name_consistency,
    check_dob_consistency,
    check_address_consistency,
    check_document_id_match,
    cross_validate_documents,
)


def _make_doc(doc_type, fields=None, ocr_text="", confidence=0.9):
    """Helper to build a processed document dict."""
    return {
        "classification": {
            "document_type": doc_type,
            "confidence": confidence,
            "extracted_fields": fields or {},
        },
        "ocr_result": {
            "text": ocr_text,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# check_name_consistency
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckNameConsistency:
    def test_consistent_names(self):
        docs = [
            _make_doc("pan_card", {"name": "Rajesh Kumar"}),
            _make_doc("pan_card", {"name": "rajesh kumar"}),
        ]
        ok, issues = check_name_consistency(docs)
        assert ok is True
        assert issues == []

    def test_mismatched_names(self):
        docs = [
            _make_doc("pan_card", {"name": "Rajesh Kumar"}),
            _make_doc("pan_card", {"name": "Suresh Kumar"}),
        ]
        ok, issues = check_name_consistency(docs)
        assert ok is False
        assert len(issues) == 1

    def test_single_doc(self):
        docs = [_make_doc("pan_card", {"name": "Rajesh"})]
        ok, issues = check_name_consistency(docs)
        assert ok is True

    def test_no_name_fields(self):
        docs = [
            _make_doc("utility_bill", {"amount": "500"}),
            _make_doc("bank_statement", {"ifsc_code": "SBIN0001234"}),
        ]
        ok, issues = check_name_consistency(docs)
        assert ok is True

    def test_whitespace_normalization(self):
        docs = [
            _make_doc("pan_card", {"name": "  Rajesh   Kumar  "}),
            _make_doc("pan_card", {"name": "Rajesh Kumar"}),
        ]
        ok, issues = check_name_consistency(docs)
        assert ok is True


# ═══════════════════════════════════════════════════════════════════════════
# check_dob_consistency
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckDOBConsistency:
    def test_consistent(self):
        docs = [
            _make_doc("pan_card", {"date_of_birth": "15/03/1990"}),
            _make_doc("aadhaar_card", {"date_of_birth": "15/03/1990"}),
        ]
        ok, issues = check_dob_consistency(docs)
        assert ok is True

    def test_different_separators_normalize(self):
        docs = [
            _make_doc("pan_card", {"date_of_birth": "15/03/1990"}),
            _make_doc("aadhaar_card", {"date_of_birth": "15-03-1990"}),
        ]
        ok, issues = check_dob_consistency(docs)
        assert ok is True

    def test_mismatch(self):
        docs = [
            _make_doc("pan_card", {"date_of_birth": "15/03/1990"}),
            _make_doc("aadhaar_card", {"date_of_birth": "16/03/1990"}),
        ]
        ok, issues = check_dob_consistency(docs)
        assert ok is False
        assert len(issues) == 1

    def test_single_dob(self):
        docs = [_make_doc("pan_card", {"date_of_birth": "15/03/1990"})]
        ok, issues = check_dob_consistency(docs)
        assert ok is True


# ═══════════════════════════════════════════════════════════════════════════
# check_document_id_match
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckDocumentIDMatch:
    def test_consistent_ids(self):
        docs = [
            _make_doc("aadhaar_card", {"aadhaar_number": "2345 6789 0123"}),
            _make_doc("bank_statement", {"aadhaar_number": "234567890123"}),
        ]
        ok, issues = check_document_id_match(docs)
        assert ok is True

    def test_mismatched_ids(self):
        docs = [
            _make_doc("aadhaar_card", {"aadhaar_number": "2345 6789 0123"}),
            _make_doc("bank_statement", {"aadhaar_number": "234567890124"}),
        ]
        ok, issues = check_document_id_match(docs)
        assert ok is False
        assert len(issues) == 1
        assert "aadhaar_number" in issues[0]

    def test_no_overlapping_ids(self):
        docs = [
            _make_doc("aadhaar_card", {"aadhaar_number": "234567890123"}),
            _make_doc("pan_card", {"pan_number": "ABCPD1234E"}),
        ]
        ok, issues = check_document_id_match(docs)
        assert ok is True

    def test_empty_docs(self):
        ok, issues = check_document_id_match([])
        assert ok is True
        assert issues == []

    def test_single_doc_no_comparison(self):
        docs = [_make_doc("aadhaar_card", {"aadhaar_number": "234567890123"})]
        ok, issues = check_document_id_match(docs)
        assert ok is True


# ═══════════════════════════════════════════════════════════════════════════
# cross_validate_documents (unified API)
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossValidateDocuments:
    def test_all_consistent(self):
        docs = [
            _make_doc("pan_card", {
                "name": "Rajesh Kumar",
                "date_of_birth": "15/03/1990",
                "pan_number": "ABCPD1234E",
            }),
            _make_doc("aadhaar_card", {
                "name": "Rajesh Kumar",
                "date_of_birth": "15/03/1990",
                "aadhaar_number": "234567890123",
            }),
        ]
        result = cross_validate_documents(docs)
        assert result["is_consistent"] is True
        assert result["all_issues"] == []
        assert result["checks"]["name"]["consistent"] is True
        assert result["checks"]["dob"]["consistent"] is True
        assert result["checks"]["document_id"]["consistent"] is True

    def test_name_mismatch_flagged(self):
        docs = [
            _make_doc("pan_card", {"name": "Rajesh Kumar"}),
            _make_doc("pan_card", {"name": "Suresh Kumar"}),
        ]
        result = cross_validate_documents(docs)
        assert result["is_consistent"] is False
        assert result["checks"]["name"]["consistent"] is False
        assert len(result["all_issues"]) >= 1

    def test_dob_mismatch_flagged(self):
        docs = [
            _make_doc("pan_card", {"date_of_birth": "15/03/1990"}),
            _make_doc("aadhaar_card", {"date_of_birth": "20/04/1991"}),
        ]
        result = cross_validate_documents(docs)
        assert result["is_consistent"] is False
        assert result["checks"]["dob"]["consistent"] is False

    def test_empty_docs(self):
        result = cross_validate_documents([])
        assert result["is_consistent"] is True
        assert result["all_issues"] == []

    def test_document_id_mismatch(self):
        docs = [
            _make_doc("aadhaar_card", {"aadhaar_number": "234567890123"}),
            _make_doc("bank_statement", {"aadhaar_number": "999988887777"}),
        ]
        result = cross_validate_documents(docs)
        assert result["is_consistent"] is False
        assert result["checks"]["document_id"]["consistent"] is False
