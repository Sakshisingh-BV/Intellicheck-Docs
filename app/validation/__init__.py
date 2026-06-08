# app/validation/__init__.py
from .validators import (
    validate_pan,
    validate_aadhaar,
    validate_passport,
    validate_pincode,
    validate_date,
    validate_ifsc,
    validate_extracted_fields,
)
from .proof_check import (
    check_required_proofs,
    check_name_match,
    check_dob_match,
    check_address_match,
    generate_status,
)

__all__ = [
    "validate_pan", "validate_aadhaar", "validate_passport",
    "validate_pincode", "validate_date", "validate_ifsc",
    "validate_extracted_fields",
    "check_required_proofs", "check_name_match", "check_dob_match",
    "check_address_match", "generate_status",
]
