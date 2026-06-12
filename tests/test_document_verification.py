#!/usr/bin/env python
"""
Manual end-to-end test script for Document Verification.

Flow:
    Enter Customer Address → Provide Document Paths → OCR → Classification
    → Address Verification → Field Validation → Proof Checks → CLEAR/REVIEW/REJECT

Usage:
    python tests/test_document_verification.py

Supports: PDF, JPG, JPEG, PNG
"""

import os
import sys
import numpy as np

# Ensure project root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


# ── Input helpers ─────────────────────────────────────────────────────────

def get_customer_address() -> dict:
    """Prompt user for customer address fields."""
    print("\n" + "=" * 50)
    print("ENTER CUSTOMER ADDRESS")
    print("=" * 50)

    line1 = input("Address Line 1: ").strip()
    city = input("City: ").strip()
    state = input("State: ").strip()
    pincode = input("Pincode: ").strip()

    return {
        "line1": line1,
        "city": city,
        "state": state,
        "pincode": pincode,
    }


def get_document_paths() -> list:
    """Prompt user for document file paths."""
    print("\n" + "=" * 50)
    print("PROVIDE DOCUMENT PATHS")
    print("=" * 50)
    print("Enter file paths one per line. Empty line to finish.")
    print(f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}\n")

    paths = []
    while True:
        path = input(f"Document {len(paths) + 1}: ").strip()
        if not path:
            break

        # Strip quotes (drag-and-drop often wraps in quotes)
        path = path.strip('"').strip("'")

        if not os.path.isfile(path):
            print(f"  [X] File not found: {path}")
            continue

        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            print(f"  [X] Unsupported format: {ext}")
            continue

        paths.append(path)
        print(f"  [OK] Added: {os.path.basename(path)}")

    return paths


# ── Core processing ──────────────────────────────────────────────────────

def process_documents(file_paths: list) -> list:
    """
    Process all documents through the full pipeline.
    PDFs are parsed via the project's PDFParser module.
    Returns list of processed document dicts.
    """
    from app.services.document_processor import DocumentProcessor

    processor = DocumentProcessor(use_minio=False)
    processed_docs = []

    for path in file_paths:
        ext = os.path.splitext(path)[1].lower()
        print(f"\nProcessing: {os.path.basename(path)}")

        result = processor.process_document(str(path))

        if ext == ".pdf":
            # For PDFs, each page is a separate document for verification
            for page in result.get("pages", []):
                page["source_file"] = os.path.basename(path)
                processed_docs.append(page)
                doc_type = page.get("classification", {}).get("document_type", "unknown")
                confidence = page.get("classification", {}).get("confidence", 0)
                page_num = page.get("page_number", "?")
                print(f"  Page {page_num}: {doc_type} (confidence: {confidence:.2f})")
        else:
            result["source_file"] = os.path.basename(path)
            processed_docs.append(result)
            doc_type = result.get("classification", {}).get("document_type", "unknown")
            confidence = result.get("classification", {}).get("confidence", 0)
            print(f"  Detected: {doc_type} (confidence: {confidence:.2f})")

    return processed_docs


# ── Output formatting ────────────────────────────────────────────────────

def format_address(addr: dict) -> str:
    """Format address dict to a single line."""
    parts = [addr.get("line1", ""), addr.get("city", ""),
             addr.get("state", ""), addr.get("pincode", "")]
    return ", ".join(p for p in parts if p)


def print_results(customer_address, processed_docs, addr_result, proof_result):
    """Print human-readable verification results."""
    print("\n")
    print("=" * 50)
    print("DOCUMENT VERIFICATION RESULT")
    print("=" * 50)

    # Customer address
    print(f"\nCustomer Address:")
    print(f"  {format_address(customer_address)}")

    # Documents detected
    print(f"\nDocuments Detected:")
    for doc in processed_docs:
        doc_type = doc["classification"]["display_name"]
        confidence = doc["classification"]["confidence"]
        source = doc.get("source_file", doc.get("filename", ""))
        if doc["classification"]["document_type"] == "unknown":
            print(f"  [X] {doc_type} ({source})")
        else:
            print(f"  [OK] {doc_type} [{confidence:.0%}] ({source})")

    # Extracted fields per document
    print(f"\nExtracted Fields:")
    for doc in processed_docs:
        doc_type = doc["classification"]["document_type"]
        fields = doc["classification"].get("extracted_fields", {})
        if fields:
            print(f"  {doc_type}:")
            for k, v in fields.items():
                print(f"    {k}: {v}")

    # Address verification
    print(f"\nAddress Verification:")
    print(f"  Status: {addr_result.get('overall_status', 'N/A')}")
    if addr_result.get("matches"):
        for match in addr_result["matches"]:
            src = match.get("doc_source", "unknown")
            status = match.get("status", "N/A")
            conf = match.get("confidence", 0)
            print(f"    {src}: {status} ({conf:.0%})")
    if addr_result.get("conflicts"):
        print(f"  Conflicts:")
        for c in addr_result["conflicts"]:
            print(f"    [!] {c}")
    if addr_result.get("freshness_issues"):
        print(f"  Freshness Issues:")
        for f in addr_result["freshness_issues"]:
            print(f"    [!] {f}")

    # Field validation
    print(f"\nField Validation:")
    field_validations = proof_result.get("field_validation", [])
    if field_validations:
        for fv in field_validations:
            dt = fv.get("doc_type", "unknown")
            for fname, fresult in fv.get("results", {}).items():
                status = "VALID" if fresult["is_valid"] else "INVALID"
                mark = "[OK]" if fresult["is_valid"] else "[X]"
                reason = f" - {fresult['reason']}" if fresult["reason"] else ""
                print(f"  {mark} {dt}.{fname}: {status}{reason}")
    else:
        print("  No fields to validate")

    # Cross-document checks
    print(f"\nCross-Document Checks:")

    name_check = proof_result.get("name_check", {})
    name_ok = name_check.get("consistent", True)
    print(f"  Name Match:    {'YES' if name_ok else 'NO'}")
    if not name_ok:
        for m in name_check.get("mismatches", []):
            print(f"    [!] {m}")

    dob_check = proof_result.get("dob_check", {})
    dob_ok = dob_check.get("consistent", True)
    print(f"  DOB Match:     {'YES' if dob_ok else 'NO'}")
    if not dob_ok:
        for m in dob_check.get("mismatches", []):
            print(f"    [!] {m}")

    addr_check = proof_result.get("address_check", {})
    addr_ok = addr_check.get("consistent", True)
    print(f"  Address Match: {'YES' if addr_ok else 'NO'}")
    if not addr_ok:
        for m in addr_check.get("issues", []):
            print(f"    [!] {m}")

    # Proofs
    proofs = proof_result.get("proofs", {})
    proofs_met = proofs.get("met", False)
    print(f"\nRequired Proofs: {'MET' if proofs_met else 'NOT MET'}")
    if not proofs_met:
        for m in proofs.get("missing", []):
            print(f"  [X] Missing: {m}")

    # Final decision
    status = proof_result.get("status", "REJECT")
    status_display = {
        "PASS": "CLEAR",
        "REVIEW": "REVIEW",
        "REJECT": "REJECT",
    }.get(status, status)

    print(f"\n{'-' * 50}")
    print(f"  Final Decision: {status_display}")
    print(f"{'-' * 50}")

    if proof_result.get("reasons"):
        print(f"\nReasons:")
        for r in proof_result["reasons"]:
            print(f"  * {r}")

    print("=" * 50)


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("DOCUMENT VERIFICATION - Manual Test Script")
    print("=" * 50)

    # 1. Get customer address
    customer_address = get_customer_address()

    # 2. Get document paths
    file_paths = get_document_paths()
    if not file_paths:
        print("\nNo documents provided. Exiting.")
        return

    # 3. Process documents (OCR + Classification)
    print("\n" + "=" * 50)
    print("PROCESSING DOCUMENTS")
    print("=" * 50)
    processed_docs = process_documents(file_paths)

    # Ensure all docs have the expected keys for downstream consumers
    for doc in processed_docs:
        if "classification" not in doc:
            doc["classification"] = {
                "document_type": "unknown",
                "display_name": "Unknown Document",
                "confidence": 0.0,
                "matched_keywords": [],
                "extracted_fields": {},
                "all_scores": {},
            }

    if not processed_docs:
        print("\nNo documents could be processed. Exiting.")
        return

    # 4. Address Verification — compare customer address with documents
    print("\nRunning Address Verification...")
    from app.address_verification.extractor import AddressExtractor
    from app.address_verification.validator import AddressVerifier

    # Build address documents for the verifier
    addr_documents = []
    for doc in processed_docs:
        ocr_text = doc.get("ocr_result", {}).get("text", "")
        doc_type = doc["classification"]["document_type"]
        extracted_addr = AddressExtractor.extract_from_text(ocr_text)
        if extracted_addr:
            addr_documents.append({
                "doc_type": doc_type,
                "address": extracted_addr,
                "extracted_date": None,  # no date parsing in this test
            })

    if addr_documents:
        addr_result = AddressVerifier.verify(customer_address, addr_documents)
    else:
        addr_result = {
            "overall_status": "NO_MATCH",
            "matches": [],
            "conflicts": [],
            "freshness_issues": [],
            "is_valid": False,
        }

    # 5. Proof Check — field validation + cross-doc consistency
    print("Running Proof Checks...")
    from app.validation.proof_check import generate_status

    proof_result = generate_status(processed_docs)

    # 6. Print results
    print_results(customer_address, processed_docs, addr_result, proof_result)


if __name__ == "__main__":
    main()
