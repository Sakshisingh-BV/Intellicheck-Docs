# tests/classification/test_classifier.py
#
# Unit tests for DocumentClassifier — verifies keyword scoring,
# document type detection, and unknown/ambiguous text handling.

import pytest
from app.classification.classifier import DocumentClassifier


@pytest.fixture
def classifier():
    return DocumentClassifier()


# ─────────────────────────────────────────────────────────────────────────
# Aadhaar Card
# ─────────────────────────────────────────────────────────────────────────

AADHAAR_TEXT = """
GOVERNMENT OF INDIA
AADHAAR
Unique Identification Authority of India
DOB: 15/08/1990
Male
Rajesh Kumar
S/O Suresh Kumar
1234 5678 9012
VID: 9876 5432 1098 7654
Address: 42 MG Road, Bengaluru, Karnataka 560001
"""

def test_aadhaar_card_classification(classifier):
    result = classifier.classify(AADHAAR_TEXT)
    assert result.document_type == "aadhaar_card"
    assert result.confidence > 0.3
    assert "aadhaar" in result.matched_keywords


def test_aadhaar_card_has_high_confidence(classifier):
    result = classifier.classify(AADHAAR_TEXT)
    assert result.confidence > 0.35, (
        f"Aadhaar confidence too low: {result.confidence}"
    )


# ─────────────────────────────────────────────────────────────────────────
# PAN Card
# ─────────────────────────────────────────────────────────────────────────

PAN_TEXT = """
INCOME TAX DEPARTMENT
GOVT. OF INDIA
PERMANENT ACCOUNT NUMBER
ABCDE1234F
Name: RAJESH KUMAR
Father's Name: SURESH KUMAR
Date of Birth: 15/08/1990
Signature
"""

def test_pan_card_classification(classifier):
    result = classifier.classify(PAN_TEXT)
    assert result.document_type == "pan_card"
    assert result.confidence > 0.3
    assert "permanent account number" in result.matched_keywords


# ─────────────────────────────────────────────────────────────────────────
# Passport
# ─────────────────────────────────────────────────────────────────────────

PASSPORT_TEXT = """
REPUBLIC OF INDIA
PASSPORT
Type: P
Country Code: IND
Surname: KUMAR
Given Name: RAJESH
Nationality: INDIAN
Date of Birth: 15/08/1990
Place of Birth: BENGALURU
Date of Issue: 01/01/2020
Date of Expiry: 31/12/2030
Place of Issue: BENGALURU
A1234567
"""

def test_passport_classification(classifier):
    result = classifier.classify(PASSPORT_TEXT)
    assert result.document_type == "passport"
    assert result.confidence > 0.3


# ─────────────────────────────────────────────────────────────────────────
# Utility Bill
# ─────────────────────────────────────────────────────────────────────────

UTILITY_BILL_TEXT = """
ELECTRICITY BILL
BESCOM - Bangalore Electricity Supply Company
Consumer Number: EL-2024-56789
Meter Number: MTR-98765
Bill Date: 01/05/2024
Due Date: 15/05/2024
Previous Reading: 45230
Current Reading: 45780
Units Consumed: 550
Tariff: Domestic
Total Amount: Rs. 3,450.00
"""

def test_utility_bill_classification(classifier):
    result = classifier.classify(UTILITY_BILL_TEXT)
    assert result.document_type == "utility_bill"
    assert result.confidence > 0.3


# ─────────────────────────────────────────────────────────────────────────
# Bank Statement
# ─────────────────────────────────────────────────────────────────────────

BANK_STATEMENT_TEXT = """
STATE BANK OF INDIA
ACCOUNT STATEMENT
Account Number: 12345678901234
IFSC: SBIN0001234
MICR: 560002001
Branch: MG Road Branch
Statement Period: 01/04/2024 to 30/04/2024
Opening Balance: 25,000.00
Credit: 50,000.00
Debit: 30,000.00
Closing Balance: 45,000.00
NEFT Transfer - Ref 12345
UPI Payment
"""

def test_bank_statement_classification(classifier):
    result = classifier.classify(BANK_STATEMENT_TEXT)
    assert result.document_type == "bank_statement"
    assert result.confidence > 0.3


# ─────────────────────────────────────────────────────────────────────────
# Unknown / Edge Cases
# ─────────────────────────────────────────────────────────────────────────

def test_unknown_text_classification(classifier):
    result = classifier.classify("hello world random text nothing useful")
    assert result.document_type == "unknown"
    assert result.confidence == 0.0


def test_empty_text_classification(classifier):
    result = classifier.classify("")
    assert result.document_type == "unknown"
    assert result.confidence == 0.0


def test_none_like_text_classification(classifier):
    result = classifier.classify("   ")
    assert result.document_type == "unknown"


def test_all_scores_present(classifier):
    """All 5 document types should appear in all_scores."""
    result = classifier.classify(AADHAAR_TEXT)
    expected_types = {
        "aadhaar_card", "pan_card", "passport",
        "utility_bill", "bank_statement",
    }
    assert expected_types == set(result.all_scores.keys())


def test_disambiguation_aadhaar_vs_pan(classifier):
    """Text with both Aadhaar and PAN keywords — negative keywords
    should help disambiguate."""
    # Aadhaar-dominant text with a stray 'income tax' mention
    text = "AADHAAR UIDAI Unique Identification Authority income tax DOB Male"
    result = classifier.classify(text)
    assert result.document_type == "aadhaar_card"


def test_to_dict_serialization(classifier):
    result = classifier.classify(PAN_TEXT)
    d = result.to_dict()
    assert isinstance(d, dict)
    assert "document_type" in d
    assert "confidence" in d
    assert "extracted_fields" in d
    assert isinstance(d["confidence"], float)
