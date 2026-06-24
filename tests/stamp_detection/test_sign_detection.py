#!/usr/bin/env python3
"""
Sign Detection — Draw bounding boxes and save to data/test_outputs/

Usage:
    python tests/stamp_detection/test_sign_detection.py
        → runs on data/sign.jpg (default)

    python tests/stamp_detection/test_sign_detection.py data/sample.webp
        → runs on a specific image

    python tests/stamp_detection/test_sign_detection.py --all
        → runs on every image inside data/

    python tests/stamp_detection/test_sign_detection.py --dir path/to/folder
        → runs on every image in that folder
"""

import os
import sys
import glob
import cv2
import torch

# Fix PyTorch 2.6+ weights_only security restriction (same patch as detector.py)
_orig_torch_load = torch.load
def _torch_load_compat(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _orig_torch_load(*args, **kwargs)
torch.load = _torch_load_compat

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from ultralytics import YOLO

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_PATH     = os.path.abspath("app/models/sign_detect/best (1).pt")
OUTPUT_DIR     = "data/test_outputs"
DEFAULT_IMAGE  = "data/sign.jpg"
SUPPORTED_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")

# Colours per label  (BGR)
LABEL_COLORS = {
    "signature": (0,   0,   255),   # red
    "sign":      (0,   0,   255),   # red  (model may use either)
    "stamp":     (0,   255, 0  ),   # green
}
DEFAULT_COLOR = (255, 165, 0)       # orange for anything else
# ─────────────────────────────────────────────────────────────────────────────


def draw_and_save(model: YOLO, image_path: str, conf_threshold: float = 0.5) -> bool:
    """Run model on one image, draw bounding boxes, save to OUTPUT_DIR."""

    img = cv2.imread(image_path)
    if img is None:
        print(f"  [-] Cannot read image: {image_path}")
        return False

    results = model(img, conf=conf_threshold, verbose=False)
    boxes   = results[0].boxes

    if boxes is None or len(boxes) == 0:
        print(f"  [!] No detections in: {image_path}")
        # Still save the original so you can see it
    else:
        for i in range(len(boxes)):
            x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
            conf    = float(boxes.conf[i])
            cls_id  = int(boxes.cls[i])
            label   = model.names.get(cls_id, str(cls_id))
            color   = LABEL_COLORS.get(label.lower(), DEFAULT_COLOR)

            # Bounding box
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            # Label text
            text = f"{label} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(img, text, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        print(f"  [+] {len(boxes)} detection(s)  →  {image_path}")

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base     = os.path.splitext(os.path.basename(image_path))[0]
    out_path = os.path.join(OUTPUT_DIR, f"{base}_sign_detected.png")
    cv2.imwrite(out_path, img)
    print(f"      Saved → {out_path}")
    return True


def collect_images(args: list) -> list:
    if args and args[0] == "--dir":
        folder = args[1] if len(args) > 1 else "data"
    elif "--all" in args:
        folder = "data"
    elif args and not args[0].startswith("--"):
        return [args[0]]          # explicit single image
    else:
        return [DEFAULT_IMAGE]    # default

    images = []
    for ext in SUPPORTED_EXTS:
        images.extend(glob.glob(os.path.join(folder, f"*{ext}")))
        images.extend(glob.glob(os.path.join(folder, f"*{ext.upper()}")))
    return sorted(set(images))


def main():
    args = sys.argv[1:]
    conf_threshold = 0.25

    # Parse --conf <value> if present
    if "--conf" in args:
        try:
            idx = args.index("--conf")
            conf_threshold = float(args[idx + 1])
            args.pop(idx + 1)
            args.pop(idx)
        except Exception:
            print("[-] Invalid threshold value for --conf. Using default 0.5")

    # Load model
    if not os.path.exists(MODEL_PATH):
        print(f"[-] Model not found: {MODEL_PATH}")
        sys.exit(1)

    print(f"[*] Loading model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    print(f"[+] Model loaded. Classes: {model.names}")
    print(f"[*] Using confidence threshold: {conf_threshold}")

    images = collect_images(args)
    if not images:
        print("[!] No images found.")
        return

    print(f"\n[*] Testing on {len(images)} image(s) ...\n")
    for img_path in images:
        draw_and_save(model, img_path, conf_threshold=conf_threshold)

    print(f"\n[+] Done. Results saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
