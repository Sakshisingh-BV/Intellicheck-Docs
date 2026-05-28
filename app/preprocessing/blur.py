# app/preprocessing/blur.py

import cv2
import numpy as np


def _laplacian_score(image: np.ndarray) -> float:
    """Variance of Laplacian blur score on a grayscale image."""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def detect_blur(image: np.ndarray, threshold: float = 180.0) -> dict:
    """
    Robust blur detection using multi-region Laplacian variance.

    Strategy:
    - Split image into a 3x3 grid, compute blur score for each cell.
    - Use the MEDIAN of all cell scores (robust to one sharp/blurry corner).
    - Also compute a global score as fallback for small images.
    - Threshold 180 is tuned for real-world ID card / document photos.

    Args:
        image:      Grayscale or BGR image (before denoising — call on raw crop).
        threshold:  Laplacian variance below this → blurry.

    Returns:
        dict with keys: blur_score, is_blurry, blur_level
    """
    h, w = image.shape[:2]

    # --- Global score ---
    global_score = _laplacian_score(image)

    # --- Multi-region grid score (3x3) ---
    cell_scores = []
    rows, cols = 3, 3
    for r in range(rows):
        for c in range(cols):
            y1, y2 = int(r * h / rows), int((r + 1) * h / rows)
            x1, x2 = int(c * w / cols), int((c + 1) * w / cols)
            cell = image[y1:y2, x1:x2]
            if cell.size > 0:
                cell_scores.append(_laplacian_score(cell))

    median_score = float(np.median(cell_scores)) if cell_scores else global_score

    # Weighted combination: median is more reliable for real photos
    blur_score = round(0.4 * global_score + 0.6 * median_score, 2)

    is_blurry = bool(blur_score < threshold)

    # Human-readable severity
    if blur_score >= threshold:
        blur_level = "sharp"
    elif blur_score >= threshold * 0.6:
        blur_level = "slightly_blurry"
    elif blur_score >= threshold * 0.3:
        blur_level = "moderately_blurry"
    else:
        blur_level = "severely_blurry"

    return {
        "blur_score": float(blur_score),
        "is_blurry": is_blurry,
        "blur_level": blur_level,
    }


def sharpen_image(image: np.ndarray, strength: float = 1.5) -> np.ndarray:
    """
    Unsharp Masking sharpening for blurry images.
    Works on both grayscale and BGR images.

    strength: 1.0 = mild, 2.0 = aggressive
    """
    # Gaussian blur to create mask
    blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=3)

    # Unsharp mask: sharp = original + strength * (original - blurred)
    sharpened = cv2.addWeighted(image, 1 + strength, blurred, -strength, 0)
    return sharpened