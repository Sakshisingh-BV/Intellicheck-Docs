#!/usr/bin/env python
"""
Debug script to verify classification pipeline end-to-end.

Run: python scripts/debug_classification.py test_output.png
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.preprocessing.utils import load_image
from app.pipelines.ocr_pipeline import OCRPipeline
from app.pipelines.classification_pipeline import ClassificationPipeline

def debug_pipeline(image_path: str):
    """Debug classification step by step."""
    
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return
    
    print("\n" + "=" * 80)
    print("DEBUG: Classification Pipeline")
    print("=" * 80)
    
    # Step 1: Run OCR
    print("\n[STEP 1] Running OCR Pipeline...")
    try:
        ocr_pipeline = OCRPipeline()
        parsed_result, formatted_result, quality_info = ocr_pipeline.run(
            str(image_path),
            check_quality=False
        )
        print(f"✅ OCR completed")
        print(f"   - Parsed result type: {type(parsed_result)}")
        print(f"   - Parsed result length: {len(parsed_result)}")
        if parsed_result:
            print(f"   - First block: {json.dumps(parsed_result[0], indent=6)}")
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Extract text from parsed result
    print("\n[STEP 2] Extracting text from parsed result...")
    try:
        extracted_text = " ".join(
            item.get("text", "") for item in parsed_result
        ).strip()
        print(f"✅ Text extracted")
        print(f"   - Text length: {len(extracted_text)}")
        print(f"   - Text preview: {extracted_text[:200]}...")
        
        if not extracted_text:
            print("⚠️  WARNING: Extracted text is empty!")
    except Exception as e:
        print(f"❌ Text extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Check formatted result
    print("\n[STEP 3] Checking formatted result...")
    try:
        print(f"✅ Formatted result type: {type(formatted_result)}")
        print(f"   - Keys: {list(formatted_result.keys())}")
        if "text" in formatted_result:
            print(f"   - Contains 'text' field: ✅")
            print(f"   - Text in formatted: {formatted_result['text'][:100]}...")
        else:
            print(f"   - Contains 'text' field: ❌ MISSING!")
    except Exception as e:
        print(f"❌ Formatted result check failed: {e}")
        return
    
    # Step 4: Run Classification
    print("\n[STEP 4] Running Classification Pipeline...")
    try:
        classification_pipeline = ClassificationPipeline()
        print(f"   - Classification pipeline initialized")
        
        classification_result = classification_pipeline.run(parsed_result)
        print(f"✅ Classification completed")
        print(f"   - Result type: {type(classification_result)}")
        print(f"   - Result: {json.dumps(classification_result.to_dict(), indent=6)}")
    except Exception as e:
        print(f"❌ Classification failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Final check
    print("\n[STEP 5] Final output structure...")
    final_result = {
        "quality": quality_info,
        "ocr_result": formatted_result,
        "classification": classification_result.to_dict() if classification_result else None,
    }
    print(f"✅ Final structure:")
    print(json.dumps(final_result, indent=2))
    
    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug_classification.py <image_path>")
        sys.exit(1)
    
    debug_pipeline(sys.argv[1])
