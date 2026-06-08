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
import tempfile
import numpy as np

# Ensure project root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── PDF → Image conversion ───────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


def pdf_to_images(pdf_path: str) -> list:
    """
    Convert each page of a PDF to a temporary PNG file.
    Returns list of temp image file paths.
    """
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf_path)
    image_paths = []

    for i in range(len(doc)):
        page = doc[i]
        # Render at 300 DPI for good OCR quality
        bitmap = page.render(scale=300 / 72)
        pil_image = bitmap.to_pil()

        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=f"_page{i + 1}.png"
        )
        pil_image.save(tmp.name)
        tmp.close()
        image_paths.append(tmp.name)
        print(f"  PDF page {i + 1} -> {os.path.basename(tmp.name)}")

    doc.close()
    return image_paths


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

def process_single_image(image_path: str, ocr_pipeline, classification_pipeline) -> dict:
    """
    Run OCR + Classification on a single image.
    Returns a processed document dict compatible with proof_check.
    """
    # OCR
    parsed_result, formatted_result, quality_info = ocr_pipeline.run(
        image_path, check_quality=False
    )

    # Classification
    classification_result = classification_pipeline.run(parsed_result)

    return {
        "filename": os.path.basename(image_path),
        "ocr_result": formatted_result,
        "classification": classification_result.to_dict(),
        "quality": quality_info,
    }


def process_documents(file_paths: list) -> list:
    """
    Process all documents. PDFs are split into pages first.
    Returns list of processed document dicts.
    """
    from app.pipelines.ocr_pipeline import OCRPipeline
    from app.pipelines.classification_pipeline import ClassificationPipeline

    ocr_pipeline = OCRPipeline()
    classification_pipeline = ClassificationPipeline()

    processed_docs = []
    temp_files = []

    try:
        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            print(f"\nProcessing: {os.path.basename(path)}")

            if ext == ".pdf":
                print("  Converting PDF to images...")
                page_images = pdf_to_images(path)
                temp_files.extend(page_images)

                for img_path in page_images:
                    print(f"  Running OCR on {os.path.basename(img_path)}...")
                    doc = process_single_image(
                        img_path, ocr_pipeline, classification_pipeline
                    )
                    doc["source_file"] = os.path.basename(path)
                    processed_docs.append(doc)
            else:
                print("  Running OCR...")
                doc = process_single_image(
                    path, ocr_pipeline, classification_pipeline
                )
                doc["source_file"] = os.path.basename(path)
                processed_docs.append(doc)

            doc_type = processed_docs[-1]["classification"]["document_type"]
            confidence = processed_docs[-1]["classification"]["confidence"]
            print(f"  Detected: {doc_type} (confidence: {confidence:.2f})")

    finally:
        # Clean up temp files from PDF conversion
        for tmp in temp_files:
            try:
                os.unlink(tmp)
            except OSError:
                pass

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
