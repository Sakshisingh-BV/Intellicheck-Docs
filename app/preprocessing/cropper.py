# app/preprocessing/cropper.py

import cv2
import numpy as np


def isolate_document_region(image):
    """
    Detect the document (card/paper) in the image and crop to that region.
    Uses a combination of heavy blurring (to destroy background texture like
    wood grain) and color-space analysis to reliably separate a document
    from a textured background.
    """

    orig = image.copy()
    h_orig, w_orig = orig.shape[:2]

    # ---- Strategy 1: Heavy blur + Otsu to kill texture ----
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Very large Gaussian blur wipes out wood grain, keeps only the
    # large-scale brightness difference between card and table
    heavily_blurred = cv2.GaussianBlur(gray, (51, 51), 0)

    # Otsu on the blurred image
    _, mask_brightness = cv2.threshold(
        heavily_blurred, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # ---- Strategy 2: HSV-based wood exclusion ----
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Wood/table hue range is roughly brown (H: 5-30), medium saturation
    lower_wood = np.array([5, 25, 40])
    upper_wood = np.array([35, 200, 220])
    wood_mask = cv2.inRange(hsv, lower_wood, upper_wood)

    # The card = everything that is NOT wood
    card_mask_color = cv2.bitwise_not(wood_mask)

    # ---- Combine both masks: pixel must be bright AND not-wood ----
    combined_mask = cv2.bitwise_and(mask_brightness, card_mask_color)

    # ---- Morphological cleanup ----
    # Close gaps inside the card
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35))
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_close)

    # Remove small noise blobs
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_open)

    # ---- Find the largest contour (the card) ----
    contours, _ = cv2.findContours(
        combined_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return image

    largest = max(contours, key=cv2.contourArea)

    # Only proceed if the detected region is meaningful (>5% of image)
    if cv2.contourArea(largest) < 0.05 * h_orig * w_orig:
        return image

    # ---- Crop using bounding rectangle ----
    x, y, w, h = cv2.boundingRect(largest)

    # Small inward margin to trim any border artifacts
    margin = 5
    x1 = min(x + margin, w_orig - 1)
    y1 = min(y + margin, h_orig - 1)
    x2 = min(x + w - margin, w_orig)
    y2 = min(y + h - margin, h_orig)

    # Ensure valid crop dimensions
    if x2 <= x1 or y2 <= y1:
        return image

    cropped = orig[y1:y2, x1:x2]

    return cropped