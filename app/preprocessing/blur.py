# app/preprocessing/blur.py

import cv2


def detect_blur(image, threshold=100):
    """
    Detect image blur using Variance of Laplacian.
    """

    blur_score = cv2.Laplacian(
        image,
        cv2.CV_64F
    ).var()

    is_blurry = blur_score < threshold

    return {
        "blur_score": round(blur_score, 2),
        "is_blurry": is_blurry
    }