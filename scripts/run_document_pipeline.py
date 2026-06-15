#!/usr/bin/env python
"""
Complete document intelligence pipeline runner.

Usage:
    python scripts/run_document_pipeline.py data/estamp2.pdf --no-minio --output data/test_outputs/estamp2_result.json
    python scripts/run_document_pipeline.py sample.webp --output output/result.json
    python scripts/run_document_pipeline.py sample.webp --output output/result.json --minio

Pipeline:
    Input (PDF/Image) → Preprocessing → OCR → Classification → Stamp Detection → JSON + Visualizations

Features:
    - Accepts PDF or image files as input
    - Full preprocessing (blur detection, sharpening)
    - OCR with parser and formatter
    - Document classification
    - Stamp / signature / QR detection with bounding boxes
    - Optional MinIO integration
    - JSON output to console and file
    - Bounding-box visualization images saved alongside JSON
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


def run_pipeline(
    input_path: str,
    output_path: str = None,
    use_minio: bool = True,
    save_to_minio: bool = True
) -> dict:
    """
    Run complete document pipeline.

    Args:
        input_path: Path to input image or PDF file.
        output_path: Optional path to save JSON output.
        use_minio: If True, initialize MinIO integration (default: True).
        save_to_minio: If True, save intermediate results to MinIO (default: True).

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

    # Derive output directory from output path for saving visualizations
    output_dir = None
    if output_path:
        output_dir = str(Path(output_path).parent)

    logger.info(f"Starting pipeline for {input_path}")

    try:
        processor = DocumentProcessor(use_minio=use_minio)

        # Process document
        result = processor.process_document(
            str(input_path),
            save_minio=save_to_minio and use_minio,
            output_dir=output_dir,
        )

        # Print to console
        print("\n" + "=" * 80)
        print("DOCUMENT PROCESSING RESULT")
        print("=" * 80)
        print(json.dumps(result, indent=2, default=str))
        print("=" * 80 + "\n")

        # Save to file
        if output_path:
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
  python scripts/run_document_pipeline.py data/estamp2.pdf --no-minio --output data/test_outputs/estamp2_result.json
  python scripts/run_document_pipeline.py data/sample.webp --output data/test_outputs/sample_result.json
  python scripts/run_document_pipeline.py data/sample.webp --output data/test_outputs/sample_result.json --no-minio
        """
    )
    parser.add_argument(
        "input",
        help="Path to input document file (PDF or image)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path. Bounding-box visualizations are saved in the same directory.",
        default=None
    )
    parser.add_argument(
        "--no-minio",
        help="Disable MinIO integration (default: enabled)",
        action="store_true",
        default=False
    )

    args = parser.parse_args()

    result = run_pipeline(
        args.input,
        args.output,
        use_minio=not args.no_minio,
        save_to_minio=not args.no_minio
    )

    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
