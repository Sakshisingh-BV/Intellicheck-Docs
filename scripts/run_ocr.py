#!/usr/bin/env python
"""
Simple OCR runner.

Usage:
    python scripts/run_ocr.py path/to/image.webp
    python scripts/run_ocr.py path/to/image.webp --output output/ocr_result.json

Runs OCR pipeline only (no preprocessing, no classification).
Outputs result to console and optionally to JSON file.
"""

import sys
import argparse
import json
import logging
from pathlib import Path

# Ensure app module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipelines.ocr_pipeline import OCRPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_ocr(image_path: str, output_path: str = None) -> dict:
    """
    Run OCR pipeline on image.

    Args:
        image_path: Path to input image.
        output_path: Optional path to save JSON output.

    Returns:
        Dict with keys: parsed_result, formatted_result, quality_info, status
    """
    image_path = Path(image_path)

    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return {
            "status": "error",
            "error": f"Image not found: {image_path}"
        }

    logger.info(f"Processing {image_path}")

    try:
        pipeline = OCRPipeline()
        parsed_result, formatted_result, quality_info = pipeline.run(
            str(image_path),
            check_quality=True
        )

        result = {
            "status": "success",
            "image": str(image_path),
            "quality": quality_info,
            "parsed_result": parsed_result,
            "formatted_result": formatted_result,
        }

        # Print to console
        print("\n" + "=" * 80)
        print("OCR RESULTS")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print("=" * 80 + "\n")

        # Optionally save to file
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Saved OCR result to {output_file}")

        return result

    except Exception as e:
        logger.error(f"OCR processing failed: {e}", exc_info=True)
        result = {
            "status": "error",
            "image": str(image_path),
            "error": str(e),
        }
        print(json.dumps(result, indent=2))
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Run OCR pipeline on a single image"
    )
    parser.add_argument(
        "image",
        help="Path to input image file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file (optional)",
        default=None
    )

    args = parser.parse_args()

    result = run_ocr(args.image, args.output)
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
