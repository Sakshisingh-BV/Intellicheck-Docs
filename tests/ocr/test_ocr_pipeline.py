import os
import json

from app.pipelines.ocr_pipeline import OCRPipeline
from app.ocr.visualizer import OCRVisualizer


INPUT_IMAGE = "data/test_images/sample.jpg"

OUTPUT_DIR = "data/test_outputs"

OUTPUT_IMAGE = os.path.join(
    OUTPUT_DIR,
    "ocr_visualized.jpg"
)

OUTPUT_JSON = os.path.join(
    OUTPUT_DIR,
    "ocr_result.json"
)


def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("[INFO] Initializing OCR Pipeline...")

    pipeline = OCRPipeline()

    # ---- Run WITH preprocessing (default) ----

    print("[INFO] Running OCR Pipeline (with preprocessing)...")

    parsed_result, formatted_result, preprocess_info = pipeline.run(
        INPUT_IMAGE
    )

    print(f"\n========== PREPROCESSING INFO ==========")
    print(f"  Blur Score : {preprocess_info['blur_score']}")
    print(f"  Is Blurry  : {preprocess_info['is_blurry']}")

    print(f"\n========== OCR RESULTS (preprocessed) ==========")
    print(f"  Total text blocks: {len(parsed_result)}")

    for i, block in enumerate(parsed_result):
        print(f"  [{i+1}] \"{block['text']}\"  (conf: {block['confidence']:.2f})")

    # ---- Run WITHOUT preprocessing for comparison ----

    print("\n[INFO] Running OCR Pipeline (raw, no preprocessing)...")

    raw_parsed, raw_formatted, _ = pipeline.run(
        INPUT_IMAGE,
        preprocess=False
    )

    print(f"\n========== OCR RESULTS (raw) ==========")
    print(f"  Total text blocks: {len(raw_parsed)}")

    for i, block in enumerate(raw_parsed):
        print(f"  [{i+1}] \"{block['text']}\"  (conf: {block['confidence']:.2f})")

    # ---- Compare ----

    print(f"\n========== COMPARISON ==========")
    print(f"  Preprocessed blocks: {len(parsed_result)}")
    print(f"  Raw blocks         : {len(raw_parsed)}")

    if parsed_result:
        avg_conf_pre = sum(b["confidence"] for b in parsed_result) / len(parsed_result)
        print(f"  Avg confidence (preprocessed): {avg_conf_pre:.4f}")

    if raw_parsed:
        avg_conf_raw = sum(b["confidence"] for b in raw_parsed) / len(raw_parsed)
        print(f"  Avg confidence (raw)         : {avg_conf_raw:.4f}")

    # ---- Save outputs (from preprocessed run) ----

    print("\n[INFO] Saving OCR JSON...")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(
            formatted_result,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("[INFO] Drawing OCR Bounding Boxes...")

    OCRVisualizer.draw_boxes(
        INPUT_IMAGE,
        parsed_result,
        OUTPUT_IMAGE
    )

    print(f"\n========== OCR PIPELINE COMPLETE ==========")
    print(f"[OUTPUT IMAGE] {OUTPUT_IMAGE}")
    print(f"[OUTPUT JSON]  {OUTPUT_JSON}")


if __name__ == "__main__":
    main()