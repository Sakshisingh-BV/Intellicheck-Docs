# Intellicheck Docs (Python + MinIO Pipeline)

This project now runs as a Python-only script pipeline (no FastAPI runtime).

## Setup

```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

## Start MinIO

```bash
./minio.exe server minio-data
```

Default endpoint used by the script: `127.0.0.1:9000`  
Default bucket: `documents`

## Input File Flow (No CLI Args)

1. Put your image in project root `inputs/`.
2. Open `run_classification.py` and set:
   - `INPUT_FILENAME = "your_file_name.png"`
3. Run one command:

```bash
python run_classification.py
```

## Blur + Retry Logic

- If `is_blurry = true` on quality check:
  - script stops processing immediately
  - prompts you to upload a clearer image in `inputs/`
- If `is_blurry = false` but classification is `unknown`:
  - script sharpens the already preprocessed image one more time
  - reruns OCR + classification
  - stores retry image in MinIO as:
    - `data/<doc_id>/preprocessed/<input_stem>_preprocessed_retry.png`
  - includes retry details in output JSON under `retry_info`

## Outputs

- MinIO objects under:
  - `data/<doc_id>/original/...`
  - `data/<doc_id>/preprocessed/...`
  - `data/<doc_id>/outputs/<input_stem>_result.json`
- Local JSON file under:
  - `data/<doc_id>/<input_stem>_result.json`
