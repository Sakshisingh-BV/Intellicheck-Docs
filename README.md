# Intellicheck — Document Intelligence Platform

> **OCR · Classification · Stamp Detection · Address Verification · ID Proof Validation**

Pure Python document processing pipeline that accepts images or PDFs, extracts text via PaddleOCR, classifies document types, detects stamps/signatures (YOLOv8), verifies e-stamps, and validates ID fields. Input files from the `data/` folder, output JSON + visualizations to `data/test_outputs/`.

> **📐 Architecture Details:** See [ARCHITECTURE.md](ARCHITECTURE.md) for Mermaid diagrams, pipeline flows, and design decisions.  
> Install the **Mermaid Preview** or **Markdown Preview Mermaid Support** VS Code extension, then press **Ctrl + Shift + V** to render the diagrams.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Python 3.10+** | Tested on 3.10–3.12 |

---

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
```

Activate (PowerShell):
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

### Process a Document

Place your document (image or PDF) in the `data/` folder, then run:

```bash
python scripts/run_document_pipeline.py data/estamp2.pdf
```

Results are automatically saved to `data/test_outputs/`:
- **JSON result:** `data/test_outputs/<filename>_result.json`
- **Detection visualizations:** `data/test_outputs/<filename>_detections.png`

### Custom Output Path

```bash
python scripts/run_document_pipeline.py data/sample.webp -o data/test_outputs/custom_result.json
```

### More Examples

```bash
# Process a PDF document
python scripts/run_document_pipeline.py data/estamp2.pdf

# Process an image
python scripts/run_document_pipeline.py data/sample.webp

# Process with custom output location
python scripts/run_document_pipeline.py data/aadhaar.jpg -o results/aadhaar_result.json
```

### CLI Options

| Flag | Description |
|------|-------------|
| `input` | Path to input document file (PDF or image) |
| `-o`, `--output <path>` | Output JSON file path (default: `data/test_outputs/<filename>_result.json`). Bounding-box visualizations are saved in the same directory. |

### Supported File Formats

| Format | Extensions |
|--------|-----------|
| **Images** | `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff` |
| **PDF** | `.pdf` (multi-page supported) |

---

## Output Format

The pipeline outputs a JSON file containing:

```json
{
  "doc_id": "uuid-...",
  "filename": "estamp2.pdf",
  "file_type": "pdf",
  "status": "completed",
  "quality": {
    "blur_score": 245.7,
    "is_blurry": false,
    "blur_level": "sharp"
  },
  "ocr_result": {
    "text": "...extracted text...",
    "total_blocks": 42
  },
  "classification": {
    "document_type": "aadhaar_card",
    "confidence": 0.87,
    "matched_keywords": ["aadhaar", "uidai"],
    "extracted_fields": { "aadhaar_number": "1234 5678 9012" }
  },
  "stamp_detection": {
    "is_estamp_document": true,
    "physical_stamps_found": 2,
    "signatures_found": 1
  },
  "address_extraction": { "...extracted address fields..." },
  "field_validation": { "valid": true, "results": {} }
}
```

---

## Document Verification Test

Interactive end-to-end verification flow:

```bash
python tests/test_document_verification.py
```

The script prompts for:
1. **Customer Address** — line 1, city, state, pincode
2. **Document Paths** — enter file paths one per line (empty line to finish)

### What It Checks

| Check | Description |
|-------|-------------|
| **Document Classification** | Identifies document type (Aadhaar, PAN, Passport, etc.) with confidence score |
| **Address Verification** | Compares OCR-extracted addresses against customer address |
| **Field Validation** | Validates Aadhaar checksum, PAN format, passport number, dates |
| **Cross-Document Checks** | Verifies name, DOB, address, and document ID consistency across documents (`cross_validation.py`) |
| **Proof Requirements** | Checks that at least one ID proof and one address proof are provided |

### Verdicts

- **CLEAR** — All checks passed
- **REVIEW** — Minor issues (low confidence, partial mismatches)
- **REJECT** — Critical failures (invalid fields, missing proofs)

---

## Stamp Detection Test

```bash
python tests/stamp_detection/test_stamp_detector_simple.py
```

To test with a different image, update the image path at **line 163** of the test script.

---

## Project Structure

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete module map, pipeline diagrams, and detailed design documentation.

---

## .gitignore

Ensure these are excluded from version control:

```text
venv/
data/uploads/
data/test_outputs/
__pycache__/
.env
*.pyc
```
