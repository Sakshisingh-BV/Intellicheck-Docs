# app/preprocessing/threshold.py

import cv2
import numpy as np


def apply_adaptive_threshold(image):
    """
    Convert image into OCR-friendly binary image.

    Uses a two-stage approach:
    1. Illumination normalization via morphological closing (removes shadows
       and uneven lighting gradients across the document).
    2. Otsu's global thresholding on the normalized image for clean binarization.
    3. Morphological opening to thin any overblown text strokes.
    """

    # --- Stage 1: Normalize illumination ---
    # A large morphological closing estimates the background illumination.
    # Dividing the original by this estimate removes shadows and gradients.
    kernel_size = max(image.shape[0], image.shape[1]) // 10
    # Ensure kernel size is odd
    kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
    kernel_size = max(kernel_size, 51)  # Minimum 51

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (kernel_size, kernel_size)
    )

    # Estimate the background illumination
    background = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)

    # Normalize: divide original by background, then scale to 0-255
    # This removes shadows and uneven lighting
    normalized = cv2.divide(image, background, scale=255)

    # --- Stage 2: Otsu's thresholding on the clean, normalized image ---
    _, binarized = cv2.threshold(
        normalized, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # --- Stage 3: Light morphological cleanup ---
    # Small opening (erode then dilate) to thin overblown text strokes
    cleanup_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    binarized = cv2.morphologyEx(binarized, cv2.MORPH_OPEN, cleanup_kernel)

    return binarized