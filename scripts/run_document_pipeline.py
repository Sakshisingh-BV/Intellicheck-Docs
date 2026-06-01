#!/usr/bin/env python
"""
Complete document intelligence pipeline runner.

Usage:
    python scripts/run_document_pipeline.py sample.webp
    python scripts/run_document_pipeline.py sample.webp --output output/result.json
    python scripts/run_document_pipeline.py sample.webp --output output/result.json --minio

Pipeline:
    Image → Preprocessing → OCR → Classification → JSON Output

Features:
    - Full preprocessing (blur detection, sharpening)
    - OCR with parser and formatter
    - Document classification
    - Optional MinIO integration
    - JSON output to console and file
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
    image_path: str,
    output_path: str = None,
    use_minio: bool = True,
    save_to_minio: bool = True
) -> dict:
    """
    Run complete document pipeline.

    Args:
        image_path: Path to input image.
        output_path: Optional path to save JSON output.
        use_minio: If True, initialize MinIO integration (default: True).
        save_to_minio: If True, save intermediate results to MinIO (default: True).

    Returns:
        Processing result dict with status, OCR, classification, etc.
    """
    image_path = Path(image_path)

    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return {
            "status": "error",
            "error": f"Image not found: {image_path}",
            "filename": str(image_path)
        }

    logger.info(f"Starting pipeline for {image_path}")

    try:
        processor = DocumentProcessor(use_minio=use_minio)

        # Process document
        result = processor.process_document(
            str(image_path),
            save_minio=save_to_minio and use_minio
        )

        # Print to console
        print("\n" + "=" * 80)
        print("DOCUMENT PROCESSING RESULT")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        print("=" * 80 + "\n")

        # Optionally save to file
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Saved result to {output_file}")

        return result

    except Exception as e:
        logger.error(f"Pipeline processing failed: {e}", exc_info=True)
        result = {
            "status": "error",
            "filename": str(image_path),
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
  python scripts/run_document_pipeline.py sample.webp
  python scripts/run_document_pipeline.py sample.webp --output output/result.json
  python scripts/run_document_pipeline.py sample.webp --output output/result.json --no-minio
        """
    )
    parser.add_argument(
        "image",
        help="Path to input image file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file (optional, default: console only)",
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
        args.image,
        args.output,
        use_minio=not args.no_minio,
        save_to_minio=not args.no_minio
    )

    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
