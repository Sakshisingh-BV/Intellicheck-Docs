# tests/classification/test_field_extraction.py
#
# Unit tests for regex field extraction from OCR text.
# Validates that structured fields (Aadhaar number, PAN, passport number,
# etc.) are correctly extracted from realistic OCR output.

import pytest
from app.classification.classifier import DocumentClassifier


@pytest.fixture
def classifier():
    return DocumentClassifier()


# ─────────────────────────────────────────────────────────────────────────
# Aadhaar Number Extraction
# ─────────────────────────────────────────────────────────────────────────

class TestAadhaarFieldExtraction:

    def test_aadhaar_number_with_spaces(self, classifier):
        text = "AADHAAR UIDAI DOB: 01/01/1990 1234 5678 9012"
        result = classifier.classify(text)
        assert result.extracted_fields.get("aadhaar_number") == "1234 5678 9012"

    def test_aadhaar_number_without_spaces(self, classifier):
        text = "AADHAAR UIDAI DOB: 01/01/1990 123456789012"
        result = classifier.classify(text)
        assert "aadhaar_number" in result.extracted_fields

    def test_aadhaar_dob_extraction(self, classifier):
        text = "AADHAAR UIDAI DOB: 15/08/1990 1234 5678 9012"
        result = classifier.classify(text)
        assert result.extracted_fields.get("date_of_birth") == "15/08/1990"

    def test_aadhaar_gender_extraction(self, classifier):
        text = "AADHAAR UIDAI Male DOB: 01/01/1990 1234 5678 9012"
        result = classifier.classify(text)
        assert result.extracted_fields.get("gender", "").lower() == "male"

    def test_aadhaar_vid_extraction(self, classifier):
        text = "AADHAAR UIDAI VID: 9876 5432 1098 7654 1234 5678 9012"
        result = classifier.classify(text)
        assert "vid_number" in result.extracted_fields


# ─────────────────────────────────────────────────────────────────────────
# PAN Number Extraction
# ─────────────────────────────────────────────────────────────────────────

class TestPANFieldExtraction:

    def test_pan_number_standard(self, classifier):
        text = "PERMANENT ACCOUNT NUMBER INCOME TAX DEPARTMENT ABCDE1234F"
        result = classifier.classify(text)
        assert result.extracted_fields.get("pan_number") == "ABCDE1234F"

    def test_pan_number_mixed_case_not_matched(self, classifier):
        """PAN regex requires uppercase — lowercase should not match."""
        text = "PERMANENT ACCOUNT NUMBER INCOME TAX abcde1234f"
        result = classifier.classify(text)
        assert result.extracted_fields.get("pan_number") is None

    def test_pan_dob_extraction(self, classifier):
        text = "PERMANENT ACCOUNT NUMBER INCOME TAX DOB: 25/12/1985 ABCDE1234F"
        result = classifier.classify(text)
        assert result.extracted_fields.get("date_of_birth") == "25/12/1985"


# ─────────────────────────────────────────────────────────────────────────
# Passport Number Extraction
# ─────────────────────────────────────────────────────────────────────────

class TestPassportFieldExtraction:

    def test_passport_number(self, classifier):
        text = "REPUBLIC OF INDIA PASSPORT Nationality INDIAN A1234567"
        result = classifier.classify(text)
        assert result.extracted_fields.get("passport_number") == "A1234567"

    def test_passport_dates(self, classifier):
        text = (
            "REPUBLIC OF INDIA PASSPORT Nationality INDIAN "
            "Date of Issue: 01/06/2020 Date of Expiry: 01/06/2030 "
            "A1234567"
        )
        result = classifier.classify(text)
        assert result.extracted_fields.get("date_of_issue") == "01/06/2020"
        assert result.extracted_fields.get("date_of_expiry") == "01/06/2030"

    def test_passport_place_of_issue(self, classifier):
        text = (
            "REPUBLIC OF INDIA PASSPORT Nationality INDIAN "
            "Place of Issue: MUMBAI A1234567"
        )
        result = classifier.classify(text)
        assert "place_of_issue" in result.extracted_fields


# ─────────────────────────────────────────────────────────────────────────
# Utility Bill Field Extraction
# ─────────────────────────────────────────────────────────────────────────

class TestUtilityBillFieldExtraction:

    def test_consumer_number(self, classifier):
        text = "ELECTRICITY BILL Consumer Number: EL-2024-56789 Bill Date: 01/05/2024"
        result = classifier.classify(text)
        assert result.extracted_fields.get("consumer_number") == "EL-2024-56789"

    def test_bill_and_due_dates(self, classifier):
        text = (
            "ELECTRICITY BILL Consumer Number: 12345 "
            "Bill Date: 01/05/2024 Due Date: 15/05/2024 "
            "Total Amount: Rs. 3450.00"
        )
        result = classifier.classify(text)
        assert result.extracted_fields.get("bill_date") == "01/05/2024"
        assert result.extracted_fields.get("due_date") == "15/05/2024"

    def test_amount_extraction(self, classifier):
        text = "ELECTRICITY BILL Consumer Number: 12345 Total Amount: Rs. 3,450.00"
        result = classifier.classify(text)
        assert "amount" in result.extracted_fields


# ─────────────────────────────────────────────────────────────────────────
# Bank Statement Field Extraction
# ─────────────────────────────────────────────────────────────────────────

class TestBankStatementFieldExtraction:

    def test_account_number(self, classifier):
        text = "BANK STATEMENT Account Number: 12345678901234 IFSC: SBIN0001234"
        result = classifier.classify(text)
        assert result.extracted_fields.get("account_number") == "12345678901234"

    def test_ifsc_code(self, classifier):
        text = "BANK STATEMENT Account Number: 123456789012 IFSC: SBIN0001234"
        result = classifier.classify(text)
        assert result.extracted_fields.get("ifsc_code") == "SBIN0001234"

    def test_micr_code(self, classifier):
        text = "BANK STATEMENT Account No: 123456789012 MICR: 560002001"
        result = classifier.classify(text)
        assert result.extracted_fields.get("micr_code") == "560002001"

    def test_statement_period(self, classifier):
        text = (
            "ACCOUNT STATEMENT Account Number: 123456789012 "
            "Period: 01/04/2024 to 30/04/2024 Credit Debit"
        )
        result = classifier.classify(text)
        assert "statement_period" in result.extracted_fields


# ─────────────────────────────────────────────────────────────────────────
# Edge Cases
# ─────────────────────────────────────────────────────────────────────────

class TestFieldExtractionEdgeCases:

    def test_no_fields_for_unknown_document(self, classifier):
        result = classifier.classify("random text with no document keywords")
        assert result.extracted_fields == {}

    def test_partial_aadhaar_number_not_matched(self, classifier):
        """A 4-digit number should not be extracted as aadhaar_number."""
        text = "AADHAAR UIDAI 1234"
        result = classifier.classify(text)
        aadhaar = result.extracted_fields.get("aadhaar_number", "")
        # Should NOT match just "1234"
        assert len(aadhaar) >= 12 or aadhaar == ""

    def test_ocr_noise_in_date(self, classifier):
        """Dates with dots instead of slashes should still be extracted."""
        text = "PERMANENT ACCOUNT NUMBER INCOME TAX DOB: 15.08.1990 ABCDE1234F"
        result = classifier.classify(text)
        assert result.extracted_fields.get("date_of_birth") == "15.08.1990"
