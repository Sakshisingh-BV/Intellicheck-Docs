#!/usr/bin/env python
"""Debug script to test the full OCR+Classification pipeline on aadhar.jpeg."""
import sys
import os
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app.pipelines.ocr_pipeline import OCRPipeline
    from app.pipelines.classification_pipeline import ClassificationPipeline

    print("=== Initializing pipelines ===")
    ocr = OCRPipeline()
    cls = ClassificationPipeline()

    image_path = os.path.join(os.path.dirname(__file__), "..", "data", "aadhar.jpeg")
    image_path = os.path.abspath(image_path)
    print(f"Image path: {image_path}")
    print(f"File exists: {os.path.exists(image_path)}")

    print("\n=== Running OCR ===")
    parsed, formatted, quality = ocr.run(image_path, check_quality=False)
    print(f"Parsed results count: {len(parsed)}")
    print(f"Formatted text (first 300 chars): {formatted.get('text', '')[:300]}")
    print(f"Quality: {quality}")

    if parsed:
        print(f"\nFirst 3 parsed entries:")
        for p in parsed[:3]:
            print(f"  text='{p.get('text', '')}' confidence={p.get('confidence', 0):.2f}")

    print("\n=== Running Classification ===")
    cls_result = cls.run(parsed)
    result_dict = cls_result.to_dict()
    print(f"Document type: {result_dict.get('document_type', 'N/A')}")
    print(f"Confidence: {result_dict.get('confidence', 0):.2f}")
    print(f"Display name: {result_dict.get('display_name', 'N/A')}")
    print(f"Matched keywords: {result_dict.get('matched_keywords', [])}")
    print(f"Extracted fields: {result_dict.get('extracted_fields', {})}")

    print("\n=== Proof Check ===")
    from app.validation.proof_check import generate_status

    doc = {
        "filename": os.path.basename(image_path),
        "ocr_result": formatted,
        "classification": result_dict,
        "quality": quality,
        "source_file": os.path.basename(image_path),
    }
    proof_result = generate_status([doc])
    print(f"Status: {proof_result.get('status', 'N/A')}")
    print(f"Reasons: {proof_result.get('reasons', [])}")
    print(f"Proofs met: {proof_result.get('proofs', {}).get('met', False)}")
    print(f"Proofs missing: {proof_result.get('proofs', {}).get('missing', [])}")

except Exception as e:
    print(f"\n=== ERROR ===")
    traceback.print_exc()
