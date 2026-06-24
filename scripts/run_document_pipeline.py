#!/usr/bin/env python
"""
Complete document intelligence pipeline runner.

Usage:
    python scripts/run_document_pipeline.py data/estamp2.pdf
    python scripts/run_document_pipeline.py data/sample.webp
    python scripts/run_document_pipeline.py data/sample.webp -o data/test_outputs/custom_result.json

Pipeline:
    Input (PDF/Image) → Preprocessing → OCR → Classification → Stamp Detection → JSON + Visualizations

Features:
    - Accepts PDF or image files as input
    - Full preprocessing (blur detection, sharpening)
    - OCR with parser and formatter
    - Document classification
    - Stamp / signature / QR detection with bounding boxes
    - JSON output to console and file
    - Bounding-box visualization images saved alongside JSON
    - Default output directory: data/test_outputs/
"""

import sys
import argparse
import json
import logging
from pathlib import Path

# Ensure app module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.document_processor import DocumentProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default output directory
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "data" / "test_outputs"


def run_pipeline(
    input_path: str,
    output_path: str = None,
) -> dict:
    """
    Run complete document pipeline.

    Args:
        input_path: Path to input image or PDF file.
        output_path: Optional path to save JSON output.
                     Defaults to data/test_outputs/<input_filename>_result.json.

    Returns:
        Processing result dict with status, OCR, classification, stamp detection, etc.
    """
    input_path = Path(input_path)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return {
            "status": "error",
            "error": f"Input file not found: {input_path}",
            "filename": str(input_path)
        }

    # Default output path: data/test_outputs/<filename>_result.json
    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(DEFAULT_OUTPUT_DIR / f"{input_path.stem}_result.json")

    # Derive output directory from output path for saving visualizations
    output_dir = str(Path(output_path).parent)

    logger.info(f"Starting pipeline for {input_path}")

    try:
        processor = DocumentProcessor()

        # Process document
        result = processor.process_document(
            str(input_path),
            output_dir=output_dir,
        )

        # Print to console
        print("\n" + "=" * 80)
        print("DOCUMENT PROCESSING RESULT")
        print("=" * 80)
        print(json.dumps(result, indent=2, default=str))
        print("=" * 80 + "\n")

        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Saved result to {output_file}")

        return result

    except Exception as e:
        logger.error(f"Pipeline processing failed: {e}", exc_info=True)
        result = {
            "status": "error",
            "filename": str(input_path),
            "error": str(e),
        }
        print(json.dumps(result, indent=2))
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Run complete document intelligence pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_document_pipeline.py data/estamp2.pdf
  python scripts/run_document_pipeline.py data/sample.webp
  python scripts/run_document_pipeline.py data/sample.webp -o data/test_outputs/custom_result.json
        """
    )
    parser.add_argument(
        "input",
        help="Path to input document file (PDF or image)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (default: data/test_outputs/<filename>_result.json). "
             "Bounding-box visualizations are saved in the same directory.",
        default=None
    )

    args = parser.parse_args()

    result = run_pipeline(
        args.input,
        args.output,
    )

    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
