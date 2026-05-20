# app/preprocessing/contrast.py

import cv2


def apply_clahe(image):
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    for contrast enhancement.

    Accepts BGR or grayscale input.
    Returns a grayscale enhanced image.
    """

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    clahe = cv2.createCLAHE(
        clipLimit=1.5,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(gray)

    return enhanced