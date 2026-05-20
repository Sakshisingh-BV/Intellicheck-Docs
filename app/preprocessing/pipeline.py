import cv2

from app.preprocessing.utils import load_image
from app.preprocessing.cropper import isolate_document_region
from app.preprocessing.rotation import correct_rotation
from app.preprocessing.contrast import apply_clahe
from app.preprocessing.denoise import denoise_image
from app.preprocessing.threshold import apply_adaptive_threshold
from app.preprocessing.blur import detect_blur


def process_image(image_path):

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

    return {
        "processed_image": binarized,
        "blur_score": blur_result["blur_score"],
        "is_blurry": blur_result["is_blurry"]
    }