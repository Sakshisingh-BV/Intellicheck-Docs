> ### 🚨 **IMPORTANT NOTE: LOAD ARCHITECTURE DIAGRAMS**
>
> 🔴 **STEP 1:** Install the **`Mermaid Preview`** or **`Markdown Preview Mermaid Support`** extension in VS Code.
> 
> 🔴 **STEP 2:** **Save your changes** and **restart your IDE** entirely.
> 
> 🔴 **STEP 3:** Open the **`ARCHITECTURE.md`** file.
> 
> 🔴 **STEP 4:** Press **`Ctrl + Shift + V`** on your keyboard to trigger the Markdown preview and render the live pipeline diagrams.




## 1. Data Matrix Decoding (Indian e-Stamp Documents)

Some Indian e-Stamp documents use **Data Matrix codes** instead of standard QR codes.

### Install Dependency

```bash
pip install pylibdmtx
```

Add to `requirements.txt`:

```text
pylibdmtx
```

---

### QR/Data Matrix Processing

The project uses a dedicated:

```text
app/stamp_detection/qr_processor.py
```

module for decoding QR/Data Matrix codes.

Workflow:

```text
Document Image
    ↓
Data Matrix Decode (pylibdmtx)
    ↓
If decode fails:
    Grayscale
    ↓
    CLAHE Contrast Enhancement
    ↓
    2x Upscale
    ↓
    Retry Decode
```

---

### Test Decoder

### Run Tests

**Note:** Please activate the virtual environment before running the test script.

```bash
python tests/stamp_detection/test_stamp_detector_simple.py
```

### Test a Different Image

To test with a different image, update the image path in:

```text
tests/stamp_detection/test_stamp_detector_simple.py
```

Modify the image path at **line 163** and rerun the script.

# MinIO Setup README

## 1. Create Virtual Environment

```bash
python -m venv venv
```

Activate:

### PowerShell

```bash
.\venv\Scripts\Activate.ps1
```

---

## 2. Install Dependencies

```bash
pip install fastapi uvicorn minio python-multipart opencv-python
```

---

## 3. Download MinIO

Download:

https://dl.min.io/server/minio/release/windows-amd64/minio.exe

Move:

```text
minio.exe
```

inside project root.

---

## 4. Create MinIO Storage Folder

Project root:

```text
minio-data/
```

---

## 5. Run MinIO

```bash
.\minio.exe server minio-data
```

---

## 6. Open MinIO Dashboard

Terminal will show:

```text
API: http://127.0.0.1:9000
WebUI: http://127.0.0.1:xxxxx
```

Open WebUI URL in browser.

Login:

```text
username: minioadmin
password: minioadmin
```

---

## 7. Create Bucket

Create bucket:

```text
documents
```

---

## 8. Run Backend and Test Upload

Run FastAPI backend:

```bash id="c8z0fq"
uvicorn app.main:app --reload
```

Open Swagger docs:

```text id="q8d1jh"
http://127.0.0.1:8000/docs
```

Use the `/upload` endpoint to upload an image and verify that:

* image upload works successfully
* original image is stored in MinIO
* preprocessed image is stored in MinIO

---

## 9. Important About Git Push

Note: `minio.exe` is not pushed to GitHub because GitHub blocks files larger than 100 MB.

---

## 10. Important `.gitignore`

Create:

```text id="w5m2tx"
.gitignore
```

Add:

```text id="3u6yad"
venv/
minio-data/
__pycache__/
.env
```

So:

* virtual env
* MinIO storage
* cache
* secrets

GitHub pe upload na ho.

---

## 11. Document Processing Pipeline

`scripts/run_document_pipeline.py` runs the full document intelligence pipeline on a single file (PDF or image) and outputs results as JSON.

### Pipeline Flow

```text
Input (PDF/Image) → Preprocessing → OCR → Classification → Stamp Detection → JSON + Visualizations
```

- **PDF files** are automatically parsed page-by-page using the `PDFParser` module (`app/document_parsing/pdf_parser.py`).
- **Image files** (JPG, JPEG, PNG, WEBP, BMP, TIFF) are processed directly.

### Usage

```bash
python scripts/run_document_pipeline.py <input_file> [options]
```

### Options

| Flag | Description |
|------|-------------|
| `-o`, `--output <path>` | Save JSON result to a file. Bounding-box visualizations are saved in the same directory. |
| `--no-minio` | Disable MinIO integration (default: enabled). |

### Examples

```bash
# Process a PDF without MinIO, save result to JSON
python scripts/run_document_pipeline.py data/estamp2.pdf --no-minio --output data/test_outputs/estamp2_result.json

# Process an image with MinIO enabled
python scripts/run_document_pipeline.py data/sample.webp --output data/test_outputs/sample_result.json

# Process an image without MinIO
python scripts/run_document_pipeline.py data/sample.webp --output data/test_outputs/sample_result.json --no-minio
```

### Output

The pipeline prints the full JSON result to the console and optionally saves it to the specified output file. For stamp/signature/QR detections, annotated bounding-box visualization images are saved alongside the JSON output.

---

## 12. Document Verification Test

`tests/test_document_verification.py` is a manual end-to-end test script that runs the complete document verification flow interactively.

### Verification Flow

```text
Enter Customer Address → Provide Document Paths → OCR → Classification
    → Address Verification → Field Validation → Proof Checks → CLEAR / REVIEW / REJECT
```

### Supported Formats

PDF, JPG, JPEG, PNG

- **PDF files** are parsed via the `PDFParser` module — each page is processed separately through OCR, classification, and verification.
- **Image files** are processed directly.

### Usage

```bash
python tests/test_document_verification.py
```

The script will interactively prompt for:

1. **Customer Address** — line 1, city, state, pincode
2. **Document Paths** — enter file paths one per line (empty line to finish)

### What It Checks

| Check | Description |
|-------|-------------|
| **Document Classification** | Identifies document type (Aadhaar, PAN, Passport, etc.) with confidence score. |
| **Address Verification** | Compares addresses extracted from documents against the customer address. |
| **Field Validation** | Validates extracted fields (PAN format, Aadhaar checksum, pincode, dates, etc.). |
| **Cross-Document Checks** | Verifies name, DOB, and address consistency across multiple documents. |
| **Proof Requirements** | Checks that at least one ID proof and one address proof are provided. |

### Final Decision

The script outputs one of three verdicts:

- **CLEAR** — All checks passed.
- **REVIEW** — Minor issues detected (e.g., low confidence, DOB mismatch).
- **REJECT** — Critical failures (e.g., invalid fields, missing proofs).

### Example

```bash
python tests/test_document_verification.py
```

```text
==================================================
DOCUMENT VERIFICATION - Manual Test Script
==================================================

# 1. Enter customer address when prompted
# 2. Provide document file paths (PDF or images)
# 3. View results: classification, address match, field validation, final decision
```
