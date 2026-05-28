# Intellicheck-Docs

## Overview

Intellicheck-Docs is a modular Document Intelligence system built using:

* Python
* FastAPI
* PaddleOCR
* OpenCV
* YOLOv8
* PostgreSQL
* Redis
* Celery
* MinIO

The current implementation includes:

* Image preprocessing pipeline
* OCR pipeline
* OCR visualization
* Structured OCR JSON generation

---

# Project Structure

```text
Intellicheck-Docs/
│
├── app/
│   ├── ocr/
│   ├── pipelines/
│   ├── preprocessing/
│   └── ...
│
├── tests/
│   ├── ocr/
│   ├── preprocessing/
│   └── ...
│
├── data/
│   ├── test_images/
│   └── test_outputs/
│
├── requirements.txt
└── README.md
```

---

# Setup Instructions

## 1. Create Virtual Environment

### Windows (Git Bash)

```bash
python -m venv venv
source venv/Scripts/activate
```

---

# Install Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

If `requirements.txt` is unavailable, install manually:

```bash
pip install paddleocr==2.7.3
pip install paddlepaddle==2.6.2
pip install opencv-python
pip install numpy==1.26.4
```

---

# Running OCR Pipeline

## Step 1: Add Input Image

Move the image you want OCR output for into:

```text
Intellicheck-Docs/data/test_images/
```

Example:

```text
Intellicheck-Docs/data/test_images/sample.jpg
```

---

## Step 2: Create Output Directory

Create the following directory if it does not already exist:

```text
Intellicheck-Docs/data/test_outputs/
```

---

## Step 3: Change Input Image Path

Open:

```text
Intellicheck-Docs/tests/ocr/test_ocr_pipeline.py
```

Modify:

```python
INPUT_IMAGE = "data/test_images/sample.jpg"
```

to whichever image you want to test.

Example:

```python
INPUT_IMAGE = "data/test_images/invoice1.jpg"
```

---

## Step 4: Run OCR Pipeline

From the project root:

```bash
python -m tests.ocr.test_ocr_pipeline
```

---

# Outputs

The OCR pipeline generates outputs inside:

```text
Intellicheck-Docs/data/test_outputs/
```

You will get:

## 1. Preprocessed Image

This is the output after the project's custom preprocessing pipeline.


## 2. OCR Visualization Output

This contains:

* PaddleOCR detections
* bounding boxes
* recognized text

Example:

```text
ocr_visualized.jpg
```

---

## 3. OCR JSON Output

Structured OCR results in JSON format.

Example:

```text
ocr_result.json
```

---

# Current OCR Flow

```text
Input Image
    ↓
Custom Preprocessing Pipeline
    ↓
PaddleOCR Internal Processing
    ↓
OCR Detection + Recognition
    ↓
Structured JSON Output
```

---

# Notes

* The system currently supports image-based OCR.
* PDF support will be added later.
* Preprocessing is intentionally modular and can be tuned independently.
* OCR logic, preprocessing logic, and pipeline orchestration are fully separated.

---

# Future Improvements

* Multi-page PDF OCR
* Layout detection
* Table extraction
* Key-value pair extraction
* Async OCR workers using Celery
* API integration with FastAPI
* Document classification
* LLM-based semantic extraction
