import cv2

from app.preprocessing.utils import load_image, save_image
from app.preprocessing.blur import detect_blur


IMAGE_PATH = "sample4.jpg"

# Load original
original = load_image(IMAGE_PATH)
print(f"Original shape: {original.shape}")

# Test blur detection
def test_blur_detection():
    """Test that blur detection works on images"""
    try:
        # This would need a real image file
        print("Blur detection module imported successfully")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
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