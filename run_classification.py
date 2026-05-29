import io
import json
import os
import tempfile
import uuid
from pathlib import Path

import cv2

from app.pipelines.classification_pipeline import ClassificationPipeline
from app.pipelines.ocr_pipeline import OCRPipeline
from app.preprocessing.blur import detect_blur, sharpen_image
from app.preprocessing.utils import load_image
from app.services.minio_client import bucket_name, client

# --- Configure input here ---
INPUTS_DIR = Path("inputs")
DATA_DIR = Path("data")
INPUT_FILENAME = "sample8.webp"
# ----------------------------


def _upload_bytes_to_minio(object_key: str, payload: bytes, content_type: str) -> None:
    client.put_object(
        bucket_name,
        object_key,
        data=io.BytesIO(payload),
        length=len(payload),
        content_type=content_type,
    )


def _run_ocr_and_classification_from_png_bytes(
    png_bytes: bytes,
) -> tuple[dict, dict]:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        tmp_file.write(png_bytes)
        tmp_path = tmp_file.name

    try:
        ocr_pipeline = OCRPipeline()
        classification_pipeline = ClassificationPipeline()
        parsed_result, formatted_result, _ = ocr_pipeline.run(
            tmp_path,
            check_quality=False,
        )
    finally:
        os.unlink(tmp_path)

    classification_result = classification_pipeline.run(parsed_result)
    return formatted_result, classification_result.to_dict()


def run_pipeline_for_image(image_path: Path) -> dict:
    if not image_path.exists() or not image_path.is_file():
        raise FileNotFoundError(
            f"Input image not found: {image_path}. "
            "Put your file under project-root/inputs and set INPUT_FILENAME."
        )

    doc_id = str(uuid.uuid4())
    original_bytes = image_path.read_bytes()
    file_ext = image_path.suffix.lower() or ".png"
    content_type = "image/png" if file_ext == ".png" else "application/octet-stream"

    original_key = f"data/{doc_id}/original/{image_path.name}"
    _upload_bytes_to_minio(original_key, original_bytes, content_type)

    image = load_image(str(image_path))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_result = detect_blur(gray)
    preprocessed = sharpen_image(gray) if blur_result["is_blurry"] else gray
    ok, preprocessed_encoded = cv2.imencode(".png", preprocessed)
    if not ok:
        raise RuntimeError("Failed to encode preprocessed image.")
    preprocessed_bytes = preprocessed_encoded.tobytes()

    preprocessed_filename = f"{image_path.stem}_preprocessed.png"
    preprocessed_key = f"data/{doc_id}/preprocessed/{preprocessed_filename}"
    _upload_bytes_to_minio(preprocessed_key, preprocessed_bytes, "image/png")

    if blur_result["is_blurry"]:
        return {
            "doc_id": doc_id,
            "input_image": str(image_path),
            "quality": {
                "blur_score": blur_result["blur_score"],
                "is_blurry": blur_result["is_blurry"],
                "blur_level": blur_result["blur_level"],
            },
            "storage": {
                "bucket": bucket_name,
                "original_key": original_key,
                "preprocessed_key": preprocessed_key,
            },
            "status": "blurry_image_rejected",
            "message": (
                "Image is blurry. Please upload a clearer picture in the inputs folder "
                "and run the script again."
            ),
        }

    formatted_result, classification_dict = _run_ocr_and_classification_from_png_bytes(
        preprocessed_bytes
    )
    retry_info = None

    if classification_dict.get("document_type") == "unknown":
        retry_preprocessed = sharpen_image(preprocessed)
        retry_ok, retry_encoded = cv2.imencode(".png", retry_preprocessed)
        if retry_ok:
            retry_bytes = retry_encoded.tobytes()
            retry_key = (
                f"data/{doc_id}/preprocessed/{image_path.stem}_preprocessed_retry.png"
            )
            _upload_bytes_to_minio(retry_key, retry_bytes, "image/png")
            retry_ocr_result, retry_classification_dict = (
                _run_ocr_and_classification_from_png_bytes(retry_bytes)
            )
            retry_info = {
                "retry_preprocessed_key": retry_key,
                "retry_classification": retry_classification_dict,
            }
            if retry_classification_dict.get("document_type") != "unknown":
                classification_dict = retry_classification_dict
                formatted_result = retry_ocr_result

    output = {
        "doc_id": doc_id,
        "input_image": str(image_path),
        "quality": {
            "blur_score": blur_result["blur_score"],
            "is_blurry": blur_result["is_blurry"],
            "blur_level": blur_result["blur_level"],
        },
        "classification": classification_dict,
        "ocr_result": formatted_result,
        "storage": {
            "bucket": bucket_name,
            "original_key": original_key,
            "preprocessed_key": preprocessed_key,
            "json_key": f"data/{doc_id}/outputs/{image_path.stem}_result.json",
        },
        "retry_info": retry_info,
        "status": "processed_and_uploaded",
    }

    output_json_bytes = json.dumps(output, indent=2, ensure_ascii=False).encode("utf-8")
    _upload_bytes_to_minio(output["storage"]["json_key"], output_json_bytes, "application/json")

    local_doc_dir = DATA_DIR / doc_id
    local_doc_dir.mkdir(parents=True, exist_ok=True)
    local_json_path = local_doc_dir / f"{image_path.stem}_result.json"
    local_json_path.write_bytes(output_json_bytes)

    output["local_output_json"] = str(local_json_path.resolve())
    return output


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    image_path = INPUTS_DIR / INPUT_FILENAME

    output = run_pipeline_for_image(image_path)
    if output.get("status") == "blurry_image_rejected":
        input(
            "Image is blurry. Replace it with a clearer image in inputs/, "
            "then press Enter to exit and re-run."
        )
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
