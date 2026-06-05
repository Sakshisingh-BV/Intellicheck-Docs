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
