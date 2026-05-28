"""
Quick debug script — upload a 90° CW rotated image path as argv[1]
and see what the rotation detection decides.
"""
import sys, cv2, numpy as np
from PIL import Image

def debug_rotation(image_path):
    # ── EXIF check ──
    try:
        pil_img = Image.open(image_path)
        exif = pil_img.getexif()
        orientation = exif.get(274)
        print(f"[EXIF] Orientation tag = {orientation}")
    except Exception as e:
        print(f"[EXIF] Could not read: {e}")

    # ── Load image WITHOUT auto EXIF ──
    img = cv2.imread(image_path, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    if img is None:
        print("ERROR: Could not load image")
        return
    h, w = img.shape[:2]
    print(f"[IMAGE] Size = {w}x{h} (w x h)")
    print(f"[IMAGE] Aspect = {'portrait' if h > w else 'landscape'}")

    # ── Hough line analysis ──
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blurred)
    edges = cv2.Canny(enhanced, 30, 120, apertureSize=3)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)

    configs = [
        {"threshold": 80, "minLineLength": 80, "maxLineGap": 10},
        {"threshold": 50, "minLineLength": 50, "maxLineGap": 15},
        {"threshold": 30, "minLineLength": 30, "maxLineGap": 20},
    ]

    for i, cfg in enumerate(configs):
        lines = cv2.HoughLinesP(
            edges, 1, np.pi/180,
            threshold=cfg["threshold"],
            minLineLength=cfg["minLineLength"],
            maxLineGap=cfg["maxLineGap"],
        )
        num_lines = 0 if lines is None else len(lines)
        print(f"\n[CONFIG {i+1}] threshold={cfg['threshold']}, minLen={cfg['minLineLength']} -> {num_lines} lines")

        if lines is None or len(lines) < 5:
            print(f"  -> Too few lines, skipping")
            continue

        horizontal_weight = 0.0
        vertical_weight = 0.0
        v_angles = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            angle = np.degrees(np.arctan2(y2-y1, x2-x1))
            abs_angle = abs(angle)
            if abs_angle <= 30:
                horizontal_weight += length
            elif 60 <= abs_angle <= 120:
                vertical_weight += length
                v_angles.append(angle)
            elif abs_angle >= 150:
                horizontal_weight += length

        print(f"  -> horizontal_weight = {horizontal_weight:.1f}")
        print(f"  -> vertical_weight   = {vertical_weight:.1f}")
        ratio = vertical_weight / horizontal_weight if horizontal_weight > 0 else float('inf')
        print(f"  -> ratio (V/H)       = {ratio:.2f}  (need > 1.15 for rotation)")

        if vertical_weight > horizontal_weight * 1.15 and v_angles:
            median_v = float(np.median(v_angles))
            print(f"  -> median vertical angle = {median_v:.1f}")
            if median_v > 0:
                print(f"  >> DETECTED: 270 CW rotation needed")
            else:
                print(f"  >> DETECTED: 90 CW rotation needed")
        elif horizontal_weight > vertical_weight * 1.15:
            print(f"  -> Image appears UPRIGHT (no rotation needed)")
        else:
            print(f"  -> INCONCLUSIVE")

    # ── Final: run the actual function ──
    from app.preprocessing.rotation import correct_rotation
    result = correct_rotation(img, image_path=image_path)
    rh, rw = result.shape[:2]
    print(f"\n[RESULT] Output size = {rw}x{rh}")
    print(f"[RESULT] Dimensions changed: {'YES ✅' if (rw != w or rh != h) else 'NO ❌ (same as input)'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_rotation_debug.py <image_path>")
        sys.exit(1)
    debug_rotation(sys.argv[1])
