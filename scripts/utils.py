"""
Utility functions for document processing scripts.

Shared utilities for CLI scripts.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to config JSON file.

    Returns:
        Config dict, or empty dict if file not found.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_file}")
        return {}

    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def save_result(result: Dict[str, Any], output_path: str) -> bool:
    """
    Save processing result to JSON file.

    Args:
        result: Result dict to save.
        output_path: Path to output file.

    Returns:
        True if successful, False otherwise.
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Saved result to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save result: {e}")
        return False


def get_image_files(directory: str, extensions: List[str] = None) -> List[Path]:
    """
    Get all image files from a directory.

    Args:
        directory: Directory to scan.
        extensions: List of file extensions to match (default: common image formats).

    Returns:
        List of Path objects for image files.
    """
    if extensions is None:
        extensions = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"]

    directory = Path(directory)
    if not directory.exists():
        logger.warning(f"Directory not found: {directory}")
        return []

    image_files = []
    for ext in extensions:
        image_files.extend(directory.glob(f"*{ext}"))
        image_files.extend(directory.glob(f"*{ext.upper()}"))

    return sorted(set(image_files))


def print_result_summary(result: Dict[str, Any]) -> None:
    """
    Print a human-readable summary of processing result.

    Args:
        result: Processing result dict.
    """
    print("\n" + "-" * 60)
    print("SUMMARY")
    print("-" * 60)

    status = result.get("status", "unknown")
    print(f"Status: {status}")

    if status == "completed":
        doc_id = result.get("doc_id", "N/A")
        filename = result.get("filename", "N/A")
        print(f"Document ID: {doc_id}")
        print(f"Filename: {filename}")

        quality = result.get("quality", {})
        if quality:
            blur_score = quality.get("blur_score", "N/A")
            is_blurry = quality.get("is_blurry", "N/A")
            print(f"Quality - Blur Score: {blur_score}, Blurry: {is_blurry}")

        classification = result.get("classification", {})
        if classification:
            doc_type = classification.get("document_type", "N/A")
            confidence = classification.get("confidence", "N/A")
            print(f"Classification - Type: {doc_type}, Confidence: {confidence}")

        ocr_result = result.get("ocr_result", {})
        if ocr_result:
            text_blocks = ocr_result.get("text_blocks", [])
            print(f"OCR - Found {len(text_blocks)} text blocks")

    elif status == "processing_failed":
        error = result.get("error", "Unknown error")
        print(f"Error: {error}")

    print("-" * 60 + "\n")
