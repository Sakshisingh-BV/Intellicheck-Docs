import cv2

from app.preprocessing.utils import load_image
from app.preprocessing.cropper import isolate_document_region
from app.preprocessing.rotation import correct_rotation
from app.preprocessing.contrast import apply_clahe
from app.preprocessing.denoise import denoise_image
from app.preprocessing.threshold import apply_adaptive_threshold
from app.preprocessing.blur import detect_blur


def process_image(image_path):
    """
    Full preprocessing pipeline for document images.

    Returns a dict with:
        - processed_image: cleaned grayscale image (denoised + enhanced)
        - ocr_ready_image: 3-channel BGR image suitable for PaddleOCR input
        - binarized_image: black-on-white binarized image (for archival/display)
        - blur_score: Laplacian variance blur metric
        - is_blurry: whether the image is considered blurry
    """

    # Step 1: Load image
    image = load_image(image_path)

    # Step 2: Crop / Region Isolation (on color image)
    cropped = isolate_document_region(image)

    # Step 3: Rotation Correction (straighten skewed text, on color image)
    straightened = correct_rotation(cropped)

    # Step 4: Contrast Enhancement (converts to grayscale internally)
    enhanced = apply_clahe(straightened)

    # Step 5: Denoise (Non-Local Means, preserves text edges)
    denoised = denoise_image(enhanced)

    # Step 6: Blur Detection (on the denoised grayscale)
    blur_result = detect_blur(denoised)

    # Step 7: Thresholding / Binarization (produces clean black-on-white text)
    binarized = apply_adaptive_threshold(denoised)

    # Step 8: Create OCR-ready 3-channel image from denoised grayscale
    # PaddleOCR 3.5 requires 3-channel input; we use the denoised
    # (not binarized) image because neural OCR models perform better
    # on grayscale/enhanced images than hard-binarized ones.
    ocr_ready = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)

    return {
        "processed_image": denoised,
        "ocr_ready_image": ocr_ready,
        "binarized_image": binarized,
        "blur_score": blur_result["blur_score"],
        "is_blurry": blur_result["is_blurry"]
    }