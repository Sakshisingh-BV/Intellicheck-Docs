import cv2

from app.preprocessing.pipeline import process_image
from app.preprocessing.utils import load_image
from app.preprocessing.cropper import isolate_document_region
from app.preprocessing.rotation import correct_rotation


IMAGE_PATH = "sample4.jpg"

# Load original
original = load_image(IMAGE_PATH)
print(f"Original shape: {original.shape}")

# Resize helper for display
def resize_for_display(img, max_w=600):
    h_, w_ = img.shape[:2]
    if w_ > max_w:
        scale = max_w / w_
        return cv2.resize(img, (int(w_ * scale), int(h_ * scale)))
    return img

# Show original
cv2.imshow("1. Original", resize_for_display(original))

# Show cropped
cropped = isolate_document_region(original)
print(f"Cropped shape: {cropped.shape}")
cv2.imshow("2. Cropped", resize_for_display(cropped))

# Show rotation-corrected
rotated = correct_rotation(cropped)
print(f"Rotated shape: {rotated.shape}")
cv2.imshow("3. Rotation Corrected", resize_for_display(rotated))

# Full pipeline result
result = process_image(IMAGE_PATH)

print(f"\n===== PREPROCESSING RESULTS =====")
print(f"Blur Score: {result['blur_score']}")
print(f"Is Blurry: {result['is_blurry']}")
print(f"Processed shape: {result['processed_image'].shape}")

cv2.imshow("4. Final Processed", resize_for_display(result["processed_image"]))

cv2.waitKey(0)
cv2.destroyAllWindows()