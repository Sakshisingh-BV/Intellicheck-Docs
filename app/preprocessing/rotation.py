# app/preprocessing/rotation.py

import cv2
import numpy as np


def correct_rotation(image):
    """
    Detect and correct the skew/rotation of a document image.
    Uses Hough Line Transform to find dominant text line angles,
    then rotates the image to make text horizontal.

    Accepts BGR or grayscale input. Returns the same format.
    """

    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Edge detection to find text lines
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Dilate to connect text into lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    dilated = cv2.dilate(edges, kernel, iterations=1)

    # Detect lines using Probabilistic Hough Transform
    lines = cv2.HoughLinesP(
        dilated,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=100,
        maxLineGap=10
    )

    if lines is None or len(lines) == 0:
        return image

    # Collect angles of all detected lines
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))

        # Only consider near-horizontal lines (within ±45°)
        # These are most likely text lines
        if -45 < angle < 45:
            angles.append(angle)

    if not angles:
        return image

    # Use the median angle to avoid outlier influence
    median_angle = np.median(angles)

    # Only correct if skew is meaningful (> 0.5°) but not extreme (< 30°)
    if abs(median_angle) < 0.5 or abs(median_angle) > 30:
        return image

    # Rotate the image to correct the skew
    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)

    # Compute new bounding dimensions to avoid cropping corners
    cos = np.abs(rotation_matrix[0, 0])
    sin = np.abs(rotation_matrix[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)

    # Adjust the rotation matrix for the new dimensions
    rotation_matrix[0, 2] += (new_w - w) / 2
    rotation_matrix[1, 2] += (new_h - h) / 2

    rotated = cv2.warpAffine(
        image,
        rotation_matrix,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return rotated
