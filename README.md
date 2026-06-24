# Intellicheck — Document Intelligence Platform

> **OCR · Classification · Stamp Detection · Address Verification · ID Proof Validation**

Intelligent document processing pipeline that accepts images or PDFs, extracts text via PaddleOCR, classifies document types, detects stamps/signatures (YOLOv8), verifies e-stamps, and validates ID fields — all with async background processing via Celery + Redis.

> **📐 Architecture Details:** See [ARCHITECTURE.md](ARCHITECTURE.md) for Mermaid diagrams, pipeline flows, and design decisions.  
> Install the **Mermaid Preview** or **Markdown Preview Mermaid Support** VS Code extension, then press **Ctrl + Shift + V** to render the diagrams.

---

## Prerequisites

| Service | Required | Notes |
|---------|----------|-------|
| **Python 3.10+** | ✅ | Tested on 3.10–3.12 |
| **Redis** | ✅ | Message broker for Celery background tasks |
| **PostgreSQL** | ✅ | Job tracking, audit trail, result storage |
| **MinIO** | Optional | Object storage for document images |

### Install Redis (Windows)

Download and install from [Redis for Windows](https://github.com/microsoftarchive/redis/releases) or use WSL:
```bash
# WSL
sudo apt install redis-server
redis-server
```

### Install PostgreSQL (Windows)

Download from https://www.postgresql.org/download/windows/ and install with default settings.

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

### 3. Create PostgreSQL Database

```bash
psql -U postgres -c "CREATE DATABASE intellicheck;"
```

Default connection: `postgresql://postgres:postgres@localhost:5432/intellicheck`

To customize, set the environment variable:
```powershell
$env:DATABASE_URL = "postgresql://user:password@host:5432/dbname"
```

> **Note:** Database tables are auto-created when FastAPI starts — no manual schema setup needed.

---

## Running the System

### Full Production Stack (3 Terminals)

```bash
# ── Terminal 1: Redis ──
redis-server

# ── Terminal 2: Celery Worker ──
.\venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

# ── Terminal 3: FastAPI Server ──
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Optional: Start MinIO (Terminal 4)

```bash
.\minio.exe server minio-data
```

MinIO Dashboard: http://127.0.0.1:9000 (login: `minioadmin` / `minioadmin`)

> Create a bucket named **`documents`** from the MinIO dashboard.

### Open Swagger UI

Navigate to: **http://127.0.0.1:8000/docs**

---

## API Usage

### Async Upload (Default — for large files)

Upload returns instantly with a `job_id`. Processing happens in the background.

```bash
# Upload a document
curl -X POST http://localhost:8000/upload -F "file=@data/estamp2.pdf"
```

Response:
```json
{
  "job_id": "abc-123-...",
  "doc_id": "def-456-...",
  "filename": "estamp2.pdf",
  "status": "queued",
  "features": ["address", "idproof", "signature", "stamp"],
  "poll_url": "/jobs/abc-123-..."
}
```

Poll for results:
```bash
curl http://localhost:8000/jobs/abc-123-...
```

Response (while processing):
```json
{ "status": "processing", "step": "OCR" }
```

Response (when complete):
```json
{ "status": "completed", "result": { "...full pipeline output..." } }
```

### Sync Upload (for testing / small files)

Blocks until processing completes and returns the full result:
```bash
curl -X POST "http://localhost:8000/upload?sync=true" -F "file=@data/sample.webp"
```

### Feature Selection

Only run specific analysis steps (OCR + classification always run):
```bash
# Only stamp + signature detection
curl -X POST "http://localhost:8000/upload?features=stamp,signature" -F "file=@data/sample.webp"

# Only address + ID proof validation
curl -X POST "http://localhost:8000/upload?features=address,idproof" -F "file=@data/aadhaar.jpg"
```

Available features: `stamp`, `signature`, `address`, `idproof`

### Text-Only Classification

Classify document type from raw text (no file upload):
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "GOVERNMENT OF INDIA AADHAAR..."}'
```

### List / Filter Jobs

```bash
# List recent jobs
curl "http://localhost:8000/jobs?limit=10"

# Filter by status
curl "http://localhost:8000/jobs?status=completed&limit=10"
curl "http://localhost:8000/jobs?status=failed"
```

### Health Check

```bash
curl http://localhost:8000/
# {"message": "Backend running"}
```

---

## API Endpoints Summary

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/upload` | Async upload → returns `job_id` |
| `POST` | `/upload?sync=true` | Sync upload → returns full result |
| `POST` | `/upload?features=stamp,address` | Upload with feature selection |
| `GET` | `/jobs/{job_id}` | Poll job status / get result |
| `GET` | `/jobs` | List recent jobs (filterable) |
| `POST` | `/classify` | Classify text without file upload |
| `GET` | `/` | Health check |

---

## Running Without Celery/Redis/PostgreSQL (Local Testing)

CLI scripts directly call `DocumentProcessor` — no background infrastructure needed:

```bash
# Full pipeline on a single file
python scripts/run_document_pipeline.py data/estamp2.pdf --no-minio --output data/test_outputs/result.json

# Process an image
python scripts/run_document_pipeline.py data/sample.webp --no-minio --output data/test_outputs/result.json

# With MinIO enabled
python scripts/run_document_pipeline.py data/sample.webp --output data/test_outputs/result.json
```

### CLI Options

| Flag | Description |
|------|-------------|
| `-o`, `--output <path>` | Save JSON result to a file. Bounding-box visualizations are saved in the same directory. |
| `--no-minio` | Disable MinIO integration (default: enabled). |

> The `?sync=true` API mode also works without Celery — it processes synchronously. PostgreSQL is still expected for FastAPI startup table checks, but a warning is logged and the server starts normally if PostgreSQL is unavailable.

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
| **Cross-Document Checks** | Verifies name, DOB, and address consistency across documents |
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

## Environment Variables

All settings are configurable via environment variables. Defaults work for local development.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/intellicheck` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `CELERY_BROKER_URL` | Same as `REDIS_URL` | Celery message broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery result backend |
| `MAX_UPLOAD_SIZE_MB` | `100` | Maximum upload file size |
| `UPLOAD_TEMP_DIR` | `data/uploads/` | Temporary file storage |
| `JOB_RESULT_TTL_SECONDS` | `86400` | Job result TTL in Redis (24h) |
| `MINIO_ENDPOINT` | `127.0.0.1:9000` | MinIO server address |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `documents` | MinIO bucket name |
| `MINIO_SECURE` | `false` | Use HTTPS for MinIO |

---

## Project Structure

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete module map, pipeline diagrams, and detailed design documentation.

---

## .gitignore

Ensure these are excluded from version control:

```text
venv/
minio-data/
data/uploads/
__pycache__/
.env
*.pyc
```

> `minio.exe` is not pushed to GitHub (>100 MB limit). Download it from https://dl.min.io/server/minio/release/windows-amd64/minio.exe
