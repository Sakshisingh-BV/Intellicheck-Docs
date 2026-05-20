# app/preprocessing/denoise.py

import cv2


def denoise_image(image):
    """
    Remove noise from the image while preserving text edges.
    Uses Non-Local Means Denoising which is superior to simple
    median/Gaussian blur for document images as it preserves
    sharp text edges while removing background noise.

    Accepts grayscale or BGR input. Returns the same format.
    """

    if len(image.shape) == 3:
        # Color image: use fastNlMeansDenoisingColored
        denoised = cv2.fastNlMeansDenoisingColored(
            image,
            h=10,               # Filter strength for luminance
            hForColorComponents=10,  # Filter strength for color
            templateWindowSize=7,
            searchWindowSize=21
        )
    else:
        # Grayscale image: use fastNlMeansDenoising
        denoised = cv2.fastNlMeansDenoising(
            image,
            h=7,                # Filter strength (moderate to preserve text edges)
            templateWindowSize=7,
            searchWindowSize=21
        )

    return denoised
