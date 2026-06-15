# app/classification/document_rules.py
#
# Central rule configuration for document classification.
#
# To add a new document type, append a new dict to DOCUMENT_RULES.
# No classifier logic changes needed.
#
# Each rule contains:
#   type_name         – canonical machine-readable name
#   display_name      – human-readable label
#   keywords          – weighted keyword groups (primary > secondary > field_hints)
#   negative_keywords – keywords that, if present, REDUCE the score
#                       (helps disambiguate similar documents)
#   field_patterns    – regex patterns for extracting structured fields
#                       Each pattern should have a named group matching the value.

import re

# ── Keyword weight constants ─────────────────────────────────────────────────
PRIMARY_WEIGHT = 3.0
SECONDARY_WEIGHT = 2.0
FIELD_HINT_WEIGHT = 1.0
NEGATIVE_PENALTY = -2.0


DOCUMENT_RULES = [
    # ──────────────────────────────────────────────────────────────────────
    # AADHAAR CARD
    # ──────────────────────────────────────────────────────────────────────
    {
        "type_name": "aadhaar_card",
        "display_name": "Aadhaar Card",
        "keywords": {
            "primary": [
                "aadhaar", "aadhar", "uidai",
                "unique identification authority",
                "आधार",
            ],
            "secondary": [
                "government of india",
                "unique identification",
                "enrolment no",
                "enrollment no",
                "mera aadhaar",
                "meri pehchaan",
            ],
            "field_hints": [
                "vid", "dob", "male", "female",
                "date of birth", "year of birth",
                "address", "s/o", "d/o", "w/o", "c/o",
            ],
        },
        "negative_keywords": [
            "income tax", "passport", "republic of india",
            "permanent account number",
        ],
        "field_patterns": {
            "aadhaar_number": re.compile(
                r"(?<![/\-\.\d])(?P<value>[2-9]\d{3}\s\d{4}\s\d{4}|[2-9]\d{11})"
            ),
            "vid_number": re.compile(
                r"\b(?:vid|VID)\s*:?\s*(?P<value>\d{4}\s?\d{4}\s?\d{4}\s?\d{4})\b"
            ),
            "date_of_birth": re.compile(
                r"(?:dob|date\s*of\s*birth|DOB)\s*:?\s*(?P<value>\d{2}[/\-\.]\d{2}[/\-\.]\d{4})"
            ),
            "gender": re.compile(
                r"\b(?P<value>male|female|transgender|MALE|FEMALE|TRANSGENDER)\b",
                re.IGNORECASE,
            ),
            "pincode": re.compile(
                r"\b(?P<value>\d{6})\b"
            ),
        },
    },

    # ──────────────────────────────────────────────────────────────────────
    # PAN CARD
    # ──────────────────────────────────────────────────────────────────────
    {
        "type_name": "pan_card",
        "display_name": "PAN Card",
        "keywords": {
            "primary": [
                "permanent account number",
                "income tax department",
                "pan", "income tax",
            ],
            "secondary": [
                "govt. of india", "govt of india",
                "government of india",
                "it department",
            ],
            "field_hints": [
                "father", "name", "date of birth",
                "signature", "dob",
            ],
        },
        "negative_keywords": [
            "aadhaar", "uidai", "passport",
            "unique identification",
        ],
        "field_patterns": {
            "pan_number": re.compile(
                r"\b(?P<value>[A-Z]{5}\d{4}[A-Z])\b"
            ),
            "date_of_birth": re.compile(
                r"(?:dob|date\s*of\s*birth|DOB)\s*:?\s*(?P<value>\d{2}[/\-\.]\d{2}[/\-\.]\d{4})"
            ),
        },
    },

    # ──────────────────────────────────────────────────────────────────────
    # PASSPORT
    # ──────────────────────────────────────────────────────────────────────
    {
        "type_name": "passport",
        "display_name": "Passport",
        "keywords": {
            "primary": [
                "passport", "republic of india",
                "travel document",
            ],
            "secondary": [
                "nationality", "indian",
                "place of birth", "place of issue",
                "date of issue", "date of expiry",
                "given name", "surname",
                "type", "country code", "ind",
            ],
            "field_hints": [
                "emigration", "ecr", "ecnr",
                "old passport", "file number",
                "mrz", "p<ind",
            ],
        },
        "negative_keywords": [
            "aadhaar", "uidai", "pan",
            "permanent account number",
            "income tax",
        ],
        "field_patterns": {
            "passport_number": re.compile(
                r"\b(?P<value>[A-Z]\d{7})\b"
            ),
            "date_of_birth": re.compile(
                r"(?:dob|date\s*of\s*birth|DOB)\s*:?\s*(?P<value>\d{2}[/\-\.]\d{2}[/\-\.]\d{4})"
            ),
            "date_of_issue": re.compile(
                r"(?:date\s*of\s*issue)\s*:?\s*(?P<value>\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
                re.IGNORECASE,
            ),
            "date_of_expiry": re.compile(
                r"(?:date\s*of\s*expiry)\s*:?\s*(?P<value>\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
                re.IGNORECASE,
            ),
            "place_of_issue": re.compile(
                r"(?:place\s*of\s*issue)\s*:?\s*(?P<value>[A-Za-z\s]+)",
                re.IGNORECASE,
            ),
        },
    },

    # ──────────────────────────────────────────────────────────────────────
    # UTILITY BILL
    # ──────────────────────────────────────────────────────────────────────
    {
        "type_name": "utility_bill",
        "display_name": "Utility Bill",
        "keywords": {
            "primary": [
                "electricity bill", "water bill", "gas bill",
                "telephone bill", "broadband bill",
                "electricity", "consumer number",
            ],
            "secondary": [
                "bill date", "due date", "billing period",
                "meter reading", "meter number",
                "total amount", "amount payable",
                "units consumed", "tariff",
                "bill number", "invoice",
            ],
            "field_hints": [
                "connection", "supply", "load",
                "subsidy", "arrears", "surcharge",
                "previous reading", "current reading",
            ],
        },
        "negative_keywords": [
            "aadhaar", "uidai", "pan", "passport",
            "permanent account number", "income tax",
        ],
        "field_patterns": {
            "consumer_number": re.compile(
                r"(?:consumer\s*(?:no|number|id))\s*:?\s*(?P<value>[\w\-]+)",
                re.IGNORECASE,
            ),
            "bill_date": re.compile(
                r"(?:bill\s*date)\s*:?\s*(?P<value>\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
                re.IGNORECASE,
            ),
            "due_date": re.compile(
                r"(?:due\s*date)\s*:?\s*(?P<value>\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
                re.IGNORECASE,
            ),
            "amount": re.compile(
                r"(?:total\s*amount|amount\s*payable|net\s*amount)\s*:?\s*(?:rs\.?\s*)?(?P<value>[\d,]+\.?\d*)",
                re.IGNORECASE,
            ),
            "meter_number": re.compile(
                r"(?:meter\s*(?:no|number))\s*:?\s*(?P<value>[\w\-]+)",
                re.IGNORECASE,
            ),
        },
    },

    # ──────────────────────────────────────────────────────────────────────
    # BANK STATEMENT
    # ──────────────────────────────────────────────────────────────────────
    {
        "type_name": "bank_statement",
        "display_name": "Bank Statement",
        "keywords": {
            "primary": [
                "bank statement", "account statement",
                "statement of account",
                "transaction history",
            ],
            "secondary": [
                "ifsc", "micr", "branch",
                "account number", "account no",
                "opening balance", "closing balance",
                "credit", "debit",
                "account holder",
            ],
            "field_hints": [
                "cheque", "withdrawal", "deposit",
                "transfer", "neft", "rtgs", "imps", "upi",
                "interest", "charges", "balance",
                "savings", "current account",
            ],
        },
        "negative_keywords": [
            "aadhaar", "uidai", "passport",
            "permanent account number",
            "electricity", "gas bill",
        ],
        "field_patterns": {
            "account_number": re.compile(
                r"(?:account\s*(?:no|number))\s*:?\s*(?P<value>\d{9,18})",
                re.IGNORECASE,
            ),
            "ifsc_code": re.compile(
                r"(?:ifsc)\s*:?\s*(?P<value>[A-Z]{4}0[A-Z0-9]{6})",
                re.IGNORECASE,
            ),
            "micr_code": re.compile(
                r"(?:micr)\s*:?\s*(?P<value>\d{9})",
                re.IGNORECASE,
            ),
            "statement_period": re.compile(
                r"(?:period|from)\s*:?\s*(?P<value>\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\s*(?:to|-)\s*\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
                re.IGNORECASE,
            ),
        },
    },
]
