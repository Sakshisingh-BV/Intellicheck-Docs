# app/preprocessing/utils.py

import cv2


def load_image(image_path):
    """
    Load image from disk.

    Uses IMREAD_IGNORE_ORIENTATION to prevent OpenCV from auto-applying
    EXIF orientation — we handle EXIF rotation ourselves in rotation.py
    for consistent behaviour.
    """

    # Read as BGR but ignore EXIF orientation (we handle it in rotation.py)
    image = cv2.imread(
        image_path,
        cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION,
    )

    if image is None:
        raise ValueError(f"Unable to load image: {image_path}")

    return image


def save_image(output_path, image):
    """
    Save image to disk.
    """

    cv2.imwrite(output_path, image)