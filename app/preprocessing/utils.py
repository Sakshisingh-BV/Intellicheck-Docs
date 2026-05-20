# app/preprocessing/utils.py

import cv2


def load_image(image_path):
    """
    Load image from disk.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Unable to load image: {image_path}")

    return image


def save_image(output_path, image):
    """
    Save image to disk.
    """

    cv2.imwrite(output_path, image)