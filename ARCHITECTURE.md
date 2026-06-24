# Intellicheck — System Architecture

> Intelligent Document Verification Platform  
> OCR · Stamp Detection · Signature Check · Address Verification · ID Proof Validation

---

## System Overview

```mermaid
graph TB
<<<<<<< HEAD
    subgraph "🌐 Clients & API Gateway (FastAPI)"
        C["Client Application / User"]
        A1["POST /upload<br/>(Async Upload / Job Queue)"]
        A2["GET /jobs/{id}<br/>(Status & Results Polling)"]
        A3["GET /jobs<br/>(Job History List)"]
        A4["POST /classify<br/>(Text-only Classification)"]
=======
    subgraph "🌐 API Gateway (FastAPI)"
        A1["POST /upload<br/>Async Upload → job_id"]
        A1S["POST /upload?sync=true<br/>Sync Processing"]
        A2["POST /classify<br/>Text-only Classification"]
        A3["GET /jobs/{id}<br/>Poll Job Status"]
        A4["GET /jobs<br/>List All Jobs"]
        A5["GET /<br/>Health Check"]
    end

    subgraph "⚡ Background Processing"
        RD[("Redis<br/>Message Queue")]
        CW["Celery Worker<br/>━━━━━━━━━━━━━━━<br/>Lazy-loads models once<br/>Processes documents"]
>>>>>>> 07eb263e492d3dfeadd231b7bc3a77f94edacd44
    end

    subgraph "🔀 Queue & Persistence"
        RD[("Redis Broker & Temp Status<br/>(Celery Queue + 24h Expiry)")]
        PG[("PostgreSQL Database<br/>(Permanent Audit & Job Store)")]
    end

    subgraph "⚙️ Worker & Orchestration"
        W["Celery Worker Process<br/>(Document Tasks)"]
        DP["DocumentProcessor<br/>━━━━━━━━━━━━━━━<br/>Central Brain<br/>Manages all pipelines"]
    end

    subgraph "📄 Input Handling"
        PDF["PDFParser<br/>pypdfium2<br/>PDF → Page Images"]
        PRE["Preprocessor<br/>Blur Detection<br/>Image Sharpening"]
    end

    subgraph "🔍 Analysis Pipelines"
        direction TB
        OCR["OCR Pipeline<br/>━━━━━━━━━━━━<br/>PaddleOCR 3.5<br/>Text Extraction"]
        CLS["Classification<br/>━━━━━━━━━━━━<br/>Rule-Based Scoring<br/>5 Document Types"]
        STM["Stamp & Signature Detection<br/>━━━━━━━━━━━━<br/>YOLOv8 + E-Stamp<br/>QR + Anomaly"]
    end

    subgraph "✅ Verification Engine"
        direction TB
        FV["Field Validators<br/>Aadhaar · PAN · Passport<br/>Verhoeff Checksum"]
        AV["Address Verification<br/>Extract · Normalize<br/>Fuzzy Match"]
        PC["Proof Check<br/>Cross-Document<br/>PASS / REVIEW / REJECT"]
    end

    subgraph "💾 Storage"
        MIO["MinIO Object Store<br/>Original + Preprocessed"]
        PG[("PostgreSQL<br/>Job Tracking + Audit")]
    end

<<<<<<< HEAD
    %% Client Interactions
    C -->|Upload Document| A1
    C -->|Poll Status / Results| A2
    C -->|List Job History| A3
    C -->|Classify Text Directly| A4

    %% API Gateway to Queue & Persistence
    A1 -->|1. Dispatch Celery Task| RD
    A1 -->|2. Create 'queued' Job| PG
    A2 -->|Read Status/Result| PG
    A3 -->|Query Job Records| PG
    A4 -->|Direct Sync Classify| CLS

    %% Redis Queue to Celery Worker
    RD -->|3. Pick up task| W
    W -->|4. Execute Pipeline| DP
    
    %% Celery Worker to PostgreSQL Progress updates
    W -->|Update Progress Stages / Final Result| PG

    %% Core Document Processor Flow
=======
    A1 -->|"Stream to disk"| RD
    A1 -->|"Create job row"| PG
    A1S --> DP
    A2 --> CLS
    A3 --> PG
    A4 --> PG
    RD --> CW --> DP
    CW -->|"Update progress"| PG
>>>>>>> 07eb263e492d3dfeadd231b7bc3a77f94edacd44
    DP --> PDF --> PRE
    DP --> PRE
    PRE --> OCR --> CLS
    DP --> STM
    DP --> MIO
    PC --> FV
    PC --> AV

    style DP fill:#1a1a2e,stroke:#e94560,color:#fff,stroke-width:2px
    style RD fill:#e94560,color:#fff,stroke:none
    style PG fill:#0f3460,color:#fff,stroke:none
    style CW fill:#16213e,stroke:#e94560,color:#fff
    style OCR fill:#16213e,stroke:#0f3460,color:#fff
    style CLS fill:#16213e,stroke:#0f3460,color:#fff
    style STM fill:#16213e,stroke:#0f3460,color:#fff
    style PC fill:#0f3460,stroke:#e94560,color:#fff,stroke-width:2px
    style RD fill:#e94560,color:#fff,stroke:none
    style PG fill:#0f3460,color:#fff,stroke:none
    style W fill:#1a1a2e,stroke:#e94560,color:#fff
```

---

## What Happens When You Upload a Document

<<<<<<< HEAD
### Step 0: You Run These Commands in Terminal

```bash
# ── Terminal 1: Start Redis ──
redis-server

# ── Terminal 2: Start Celery Worker ──
.\venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

# ── Terminal 3: Start FastAPI ──
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
=======
```
app/
├── main.py                              ← FastAPI app factory, router registration
│
├── core/
│   └── config.py                        ← Centralized settings (limits, URLs, features)
│
├── routes/
│   ├── upload.py                        ← POST /upload (streaming + async/sync)
│   ├── classify.py                      ← POST /classify (text-only)
│   └── jobs.py                          ← GET /jobs/{id} + GET /jobs (status polling)
│
├── services/
│   ├── document_processor.py            ← Central orchestrator (features + progress)
│   └── minio_client.py                  ← MinIO object storage client
│
├── workers/
│   ├── celery_app.py                    ← Celery + Redis configuration
│   └── document_tasks.py               ← Background processing task (lazy model loading)
│
├── database/
│   ├── __init__.py                      ← Package exports (Base, Job, session helpers)
│   ├── base.py                          ← SQLAlchemy declarative base + create_tables()
│   ├── session.py                       ← PostgreSQL session factory (pool_size=5)
│   └── models.py                        ← Job model (status, step, result, audit timestamps)
│
├── schemas/
│   ├── upload.py                        ← UploadResponseSchema, UploadAcceptedSchema, QualitySchema
│   ├── classify.py                      ← ClassifyRequest, ClassifyResponse, ClassificationSchema
│   └── jobs.py                          ← JobStatusResponse, JobListResponse
│
├── document_parsing/
│   └── pdf_parser.py                    ← PDF → page images (pypdfium2, 75 DPI)
│
├── preprocessing/
│   ├── blur.py                          ← Multi-region Laplacian blur detection + sharpening
│   └── utils.py                         ← Image loading utilities (EXIF-aware)
│
├── ocr/
│   ├── engine.py                        ← PaddleOCR 3.5 wrapper (CPU, English)
│   ├── parser.py                        ← Raw OCRResult → structured blocks
│   ├── formatter.py                     ← Blocks → full text output
│   └── visualizer.py                    ← OCR bounding box visualization
│
├── classification/
│   ├── classifier.py                    ← Weighted keyword scoring engine
│   ├── document_rules.py                ← 5 document type rule configs
│   └── result.py                        ← ClassificationResult dataclass
│
├── stamp_detection/
│   ├── __init__.py                      ← Package exports (StampDetector, utils, etc.)
│   ├── detector.py                      ← YOLO orchestrator (StampDetector)
│   ├── estamp_classifier.py             ← E-stamp classifier (blur-aware OCR + scoring)
│   ├── anomaly_detector.py              ← Per-crop quality checks (faded/contrast/blur)
│   ├── qr_processor.py                  ← OpenCV QR detection & decoding
│   └── utils.py                         ← Cropping, ink check, visualization, overlap
│
├── address_verification/
│   ├── extractor.py                     ← Regex address extraction from OCR
│   ├── normalizer.py                    ← Abbreviation expansion
│   ├── matcher.py                       ← Fuzzy + containment matching
│   ├── freshness.py                     ← Document age validation
│   └── validator.py                     ← Full verification orchestrator
│
├── validation/
│   ├── validators.py                    ← Aadhaar, PAN, Passport, IFSC validators
│   └── proof_check.py                   ← Cross-doc verification → PASS/REVIEW/REJECT
│
├── pipelines/
│   ├── ocr_pipeline.py                  ← OCR orchestration
│   ├── classification_pipeline.py       ← Classification orchestration
│   └── stamp_detection_pipeline.py      ← Stamp detection orchestration
│
├── models/
│   ├── best.pt                          ← YOLO stamp/signature detection model (~22 MB)
│   ├── sign_detect/                     ← Alternative signature models
│   ├── document.py                      ← ORM model (placeholder)
│   ├── submission.py                    ← ORM model (placeholder)
│   └── extraction_result.py             ← ORM model (placeholder)
│
├── storage/                             ← Storage abstraction layer (placeholder)
└── utils/                               ← Shared utility functions (placeholder)

scripts/
└── run_document_pipeline.py             ← CLI pipeline runner (no Celery/Redis needed)
tests/
├── api/                                 ← API endpoint tests
├── classification/                      ← Classification tests
├── ocr/                                 ← OCR tests
├── pipelines/                           ← Pipeline integration tests
├── preprocessing/                       ← Preprocessing tests
├── stamp_detection/                     ← Stamp detection tests
├── test_document_verification.py        ← Cross-document verification tests
├── test_pdf_processing.py               ← PDF processing tests
├── test_validation.py                   ← Field validation tests
└── debug_pipeline.py                    ← Pipeline debugging script
>>>>>>> 07eb263e492d3dfeadd231b7bc3a77f94edacd44
```

### Step 1: Client Uploads File

```bash
# User runs this in Terminal 4:
curl -X POST http://localhost:8000/upload \
  -F "file=@data/rental_agreement.pdf" \
  -F "features=stamp,signature,address,idproof"
```

### Step 2: What Happens Inside (End-to-End)

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Terminal)
    participant API as FastAPI /upload<br/>(upload.py)
    participant Disk as data/uploads/<br/>(Temp File)
    participant DB as PostgreSQL<br/>(Permanent Store)
    participant RD as Redis<br/>(Broker & Temp Status)
    participant W as Celery Worker<br/>(document_tasks.py)
    participant DP as DocumentProcessor<br/>(Central Brain)

    User->>API: POST /upload (file + features)
    
    Note over API: Validate extension (.pdf, .jpg, .png, etc.)<br/>Parse features: {stamp, signature, address, idproof}
    
    API->>Disk: Stream file in 1 MB chunks<br/>(never loads full file into RAM)
    Note over API,Disk: Check size DURING streaming<br/>Abort if > 100 MB

    API->>DB: INSERT INTO jobs (id, status='queued', features=[...])
    API->>RD: celery.delay(process_document_task, job_id, file_path, features)
    API-->>User: { job_id: "abc-123", status: "queued", poll_url: "/jobs/abc-123" }
    
    Note over User: User is FREE — no waiting!

    RD->>W: Pick up task from queue
    W->>DB: UPDATE jobs SET status='processing', step='INITIALIZING'
    
    W->>DP: process_document(file_path, features, progress_callback)
    
    Note over DP: ── PREPROCESSING ──<br/>Load image → Blur detection → Sharpen if blurry
    DP->>W: progress_callback("PREPROCESSING")
    W->>DB: UPDATE step='PREPROCESSING'

    Note over DP: ── OCR ──<br/>PaddleOCR 3.5 extracts text + bounding boxes
    DP->>W: progress_callback("OCR")
    W->>DB: UPDATE step='OCR'
    
    Note over DP: ── CLASSIFICATION ──<br/>Score OCR text against 5 document rules<br/>→ aadhaar_card / pan_card / passport / utility_bill / bank_statement
    
    Note over DP: ── STAMP_DETECTION ──<br/>YOLOv8 + EStampClassifier + QRProcessor + AnomalyDetector
    DP->>W: progress_callback("STAMP_DETECTION")
    W->>DB: UPDATE step='STAMP_DETECTION'
    
    Note over DP: ── SIGNATURE_DETECTION ──<br/>Signatures found in same YOLO pass as stamps
    DP->>W: progress_callback("SIGNATURE_DETECTION")
    W->>DB: UPDATE step='SIGNATURE_DETECTION'
    
    Note over DP: ── ADDRESS_CHECK ──<br/>AddressExtractor: regex-based pincode/city/state/line extraction
    DP->>W: progress_callback("ADDRESS_CHECK")
    W->>DB: UPDATE step='ADDRESS_CHECK'
    
    Note over DP: ── ID_PROOF_CHECK ──<br/>validate_extracted_fields: Aadhaar checksum, PAN format, Passport format
    DP->>W: progress_callback("ID_PROOF_CHECK")
    W->>DB: UPDATE step='ID_PROOF_CHECK'
    
    DP-->>W: Complete result dict
    W->>W: progress_callback("FINALIZING")
    W->>DB: UPDATE status='completed', result={...full JSON...}
    W->>Disk: DELETE temp file (try/finally cleanup)

    User->>API: GET /jobs/abc-123
    API->>DB: SELECT * FROM jobs WHERE id='abc-123'
    API-->>User: { status: "completed", result: { stamp_detection, address_extraction, field_validation, ... } }
```

### Progress Stages (What You See When Polling)

```
INITIALIZING → PREPROCESSING → OCR → STAMP_DETECTION →
SIGNATURE_DETECTION → ADDRESS_CHECK → ID_PROOF_CHECK → FINALIZING
```

Each stage is written to PostgreSQL. When you poll `GET /jobs/{id}`, you see which stage the job is currently on.

---

## Multi-Page PDF Handling

When a PDF is uploaded, `PDFParser` (pypdfium2) renders each page as a PNG at 75 DPI. Each page goes through the **full pipeline independently** (preprocessing → OCR → classification → stamp → address → idproof). After all pages are done, results are **aggregated**.

```mermaid
graph TB
    PDF["📄 Multi-page PDF"] --> RENDER["pypdfium2<br/>Render each page → PNG"]
    RENDER --> P1["Page 1 PNG"]
    RENDER --> P2["Page 2 PNG"]
    RENDER --> P3["Page N PNG"]
    
    P1 --> PROC1["Full Pipeline<br/>Preprocess → OCR → Classify<br/>→ Stamp → Address → IDProof"]
    P2 --> PROC2["Full Pipeline<br/>Preprocess → OCR → Classify<br/>→ Stamp → Address → IDProof"]
    P3 --> PROC3["Full Pipeline<br/>Preprocess → OCR → Classify<br/>→ Stamp → Address → IDProof"]
    
    PROC1 --> AGG["Aggregate Results"]
    PROC2 --> AGG
    PROC3 --> AGG
    
    AGG --> R1["OCR: Merge all text across pages"]
    AGG --> R2["Classification: Best confidence page wins"]
    AGG --> R3["Stamps/Signatures: Union all bounding boxes"]
    AGG --> R4["Address: Extract from merged text"]

    style PDF fill:#e94560,color:#fff,stroke:none
    style AGG fill:#0f3460,color:#fff,stroke:none
```

**Aggregation Logic (from `document_processor.py`):**

| Data | Strategy | Why |
|------|----------|-----|
| **OCR Text** | Merge all pages with `\n\n` separator | Full text needed for address extraction and classification |
| **Classification** | Pick the page with highest confidence score | A 10-page rental agreement might only have the e-stamp on page 1 |
| **Stamps** | Union all bounding boxes, each tagged with `page_number` | Stamps can appear on any page |
| **Signatures** | Union all bounding boxes, each tagged with `page_number` | Signatures can appear on any page |
| **Temp PNGs** | Deleted in `finally` block after processing | Cleanup to prevent disk fill |

---

## Feature 1: Stamp & E-Stamp Check

**Goal:** Detect physical stamps, classify whether document is an e-stamp, extract certificate number, stamp duty, state, date, and read QR codes.

### What Triggers It

User includes `stamp` in features:
```bash
curl -X POST "http://localhost:8000/upload?features=stamp" -F "file=@data/estamp2.pdf"
```

In `document_processor.py` → `run_stamp = features is None or "stamp" in features or "signature" in features`

### End-to-End Flow

```mermaid
sequenceDiagram
    autonumber
    participant DP as DocumentProcessor
    participant SDP as StampDetectionPipeline
    participant DET as StampDetector
    participant YOLO as YOLOv8 Model<br/>(best.pt)
    participant ESC as EStampClassifier
    participant QR as QRProcessor<br/>(OpenCV)
    participant ANOM as AnomalyDetector

    DP->>SDP: process(image, ocr_text)
    SDP->>DET: detect(image, ocr_text)
    
    rect rgb(26, 32, 53)
        Note over DET: Step 1: YOLO Detection
        DET->>YOLO: model(image, conf=0.5)
        YOLO-->>DET: Bounding boxes + labels (stamp/sign)
        Note over DET: Parse boxes → filter by confidence<br/>Crop each detection<br/>Check ink (HSV saturation)
    end
    
    rect rgb(15, 52, 96)
        Note over DET: Step 2: E-Stamp Classification
        DET->>ESC: classify(image, ocr_text)
        Note over ESC: Regex searches on OCR text:<br/>• Certificate number: IN-MH12345678901234 (+40 pts)<br/>• Stamp duty: Rs. 100 (+25 pts)<br/>• State name: Maharashtra (+15 pts)<br/>• Date: 01/01/2024 (+10 pts)
        ESC->>QR: process(image)
        Note over QR: 1. Try cv2.QRCodeDetector().detectAndDecode()<br/>2. If failed: contour-based finder pattern search<br/>3. If QR decoded and contains certificate → +5 pts
        QR-->>ESC: {qr_present, qr_decoded, qr_data}
        Note over ESC: Total score ≥ 50 → "e_stamp"<br/>Total score < 50 → "non_e_stamp"
        ESC-->>DET: {document_type, document_fields, estamp_score}
    end
    
    rect rgb(45, 52, 54)
        Note over DET: Step 3: Anomaly Detection
        DET->>ANOM: detect_anomalies(detections)
        Note over ANOM: Per-crop quality checks:<br/>• Faded? (std < 30)<br/>• Low contrast? (range < 50)<br/>• Blurry? (Laplacian < 100)
        ANOM-->>DET: Anomaly flags per detection
    end
    
    DET-->>SDP: Full stamp result
    SDP-->>DP: Serialized JSON (numpy arrays stripped)
```

### E-Stamp Scoring Breakdown

| Signal | Points | Detection Method |
|--------|--------|-----------------|
| Certificate Number | **40** | Regex: `IN-MH12345678901234` |
| Stamp Duty Amount | **25** | Regex: `Rs. 100` (needs context — only counted if certificate/e-stamp keyword found) |
| State Name | **15** | Match against 22 Indian states |
| Date | **10** | Multiple date formats |
| QR Decoded (data) | **5** | OpenCV QRCodeDetector |
| QR Present (visual) | **2** | Contour-based finder pattern / detect() |
| **Threshold** | **50** | Score ≥ 50 → e-stamp confirmed |

> **Context-aware:** Stamp duty, state, and date only count if a certificate number OR e-stamp keyword was already found. Prevents false positives from generic invoices.

### Output JSON

```json
{
  "stamp_detection": {
    "success": true,
    "is_estamp_document": true,
    "document_type": "e_stamp",
    "document_fields": {
      "certificate_number": "IN-MH20240001234567",
      "stamp_duty": "Rs. 500",
      "state": "Maharashtra",
      "date": "15/03/2024",
      "qr_present": true,
      "qr_decoded": true,
      "qr_data": "https://shcilestamp.com/verify/IN-MH20240001234567",
      "estamp_score": 87,
      "estamp_threshold": 50
    },
    "physical_stamps_found": 1,
    "signatures_found": 2,
    "bounding_boxes": {
      "stamps": [{"label": "stamp", "confidence": 0.92, "bbox": [100, 200, 300, 400], "ink_confirmed": true}],
      "signatures": [{"label": "signature", "confidence": 0.87, "bbox": [500, 600, 700, 750]}],
      "qr_codes": []
    }
  }
}
```

---

## Feature 2: Signature Check

**Goal:** Locate signatures in the document, distinguish them from stamps, and report presence.

### What Triggers It

User includes `signature` (or `stamp`) in features:
```bash
curl -X POST "http://localhost:8000/upload?features=signature" -F "file=@data/agreement.jpg"
```

In `document_processor.py` → `run_stamp = features is None or "stamp" in features or "signature" in features`

> **Important:** Stamp and signature detection share the **same YOLO pass**. The YOLOv8 model (`best.pt`) is trained to detect both classes: `stamp` and `sign` (mapped to `signature`). Requesting either feature runs the full stamp detection pipeline.

### End-to-End Flow

```mermaid
sequenceDiagram
    autonumber
    participant DP as DocumentProcessor
    participant SDP as StampDetectionPipeline
    participant DET as StampDetector
    participant YOLO as YOLOv8 Model

    DP->>SDP: process(image, ocr_text)
    SDP->>DET: detect(image, ocr_text)
    
    DET->>YOLO: model(image, conf=0.5)
    YOLO-->>DET: Raw detections with class IDs

    Note over DET: For each detection:<br/>class_id → model.names → app label<br/>"stamp" → "stamp"<br/>"sign" → "signature"
    
    Note over DET: Per-class confidence thresholds:<br/>Stamp: conf ≥ 0.5<br/>Signature: conf ≥ 0.5
    
    Note over DET: For stamps only:<br/>Crop → HSV saturation check<br/>→ ink_confirmed: true/false
    
    Note over DET: For all detections:<br/>AnomalyDetector checks crop quality<br/>(faded, low contrast, blurry)

    DET-->>SDP: {detections: [{label: "signature", confidence: 0.89, bbox: [...]}]}
    SDP-->>DP: Serialized result
```

### How Stamps vs Signatures Are Distinguished

```mermaid
graph LR
    YOLO["YOLOv8 Raw Output"] --> C1{"Class = 'stamp'?"}
    YOLO --> C2{"Class = 'sign'?"}
    
    C1 -->|Yes| S1["label: 'stamp'<br/>+ ink check (HSV)"]
    C2 -->|Yes| S2["label: 'signature'<br/>no ink check"]
    
    S1 --> OUT["Final detections[]"]
    S2 --> OUT
    
    style S1 fill:#e94560,color:#fff,stroke:none
    style S2 fill:#0f3460,color:#fff,stroke:none
```

| Aspect | Stamp | Signature |
|--------|-------|-----------|
| **YOLO class** | `stamp` | `sign` (mapped to `signature`) |
| **Ink check** | ✅ HSV saturation analysis | ❌ Not applicable |
| **Anomaly check** | ✅ Faded/contrast/blur | ✅ Faded/contrast/blur |
| **Threshold** | `confidence_threshold` (0.5) | `signature_confidence_threshold` (0.5) |

### Output JSON

```json
{
  "stamp_detection": {
    "signatures_found": 2,
    "bounding_boxes": {
      "signatures": [
        {"label": "signature", "confidence": 0.89, "bbox": [120, 450, 380, 520], "anomalies": []},
        {"label": "signature", "confidence": 0.76, "bbox": [500, 800, 720, 870], "anomalies": ["faded"]}
      ]
    }
  }
}
```

---

## Feature 3: Address Check

**Goal:** Extract structured address from OCR text (pincode, city, state, address line). When multiple documents are submitted, compare addresses across them using fuzzy matching.

### What Triggers It

User includes `address` in features:
```bash
curl -X POST "http://localhost:8000/upload?features=address" -F "file=@data/aadhaar.jpg"
```

In `document_processor.py` → `run_address = features is None or "address" in features`

### End-to-End Flow (Single Document)

```mermaid
sequenceDiagram
    autonumber
    participant DP as DocumentProcessor
    participant OCR as OCR Result<br/>(already extracted)
    participant EXT as AddressExtractor
    
    DP->>OCR: Get formatted_result.text
    DP->>EXT: extract_from_text(ocr_text)
    
    Note over EXT: 1. Extract Pincode<br/>Regex: 6-digit number (first digit 1-9)<br/>Tries "PIN Code: 400001" first, then standalone

    Note over EXT: 2. Extract State<br/>Match against 32 Indian states/UTs<br/>Tries "State: Maharashtra" first, then text scan

    Note over EXT: 3. Extract City<br/>Match against 45+ Indian cities<br/>Tries "City: Mumbai" first, then text scan

    Note over EXT: 4. Extract Address Line<br/>Strategy: find text before pincode/city/state<br/>Tries "Address:" labeled field first<br/>Strips D/O, S/O prefixes

    EXT-->>DP: {line1, city, state, pincode}
    
    Note over DP: Needs at least pincode OR (city + state)<br/>to return a result. Otherwise returns None.
```

### Cross-Document Address Matching (via proof_check.py)

When multiple documents are submitted together, `check_address_match()` compares them:

```mermaid
graph TB
    D1["Doc 1: Aadhaar<br/>OCR Text"] --> E1["AddressExtractor<br/>{line1, city, state, pincode}"]
    D2["Doc 2: Utility Bill<br/>OCR Text"] --> E2["AddressExtractor<br/>{line1, city, state, pincode}"]
    D3["Doc 3: Passport<br/>OCR Text"] --> E3["AddressExtractor<br/>{line1, city, state, pincode}"]

    E1 --> MAT["AddressMatcher.compare()"]
    E2 --> MAT
    E3 --> MAT

    MAT --> P1["Pincode: Exact match"]
    MAT --> P2["State: Exact match"]
    MAT --> P3["City: Fuzzy match (≥ 0.85)"]
    MAT --> P4["Line1: Fuzzy + Containment"]

    P1 --> DEC{Decision}
    P2 --> DEC
    P3 --> DEC
    P4 --> DEC

    DEC -->|"pin+state+3 fields"| MATCH["✅ MATCH"]
    DEC -->|"pin+state only"| PARTIAL["⚠️ PARTIAL_MATCH"]
    DEC -->|"fail"| NOMATCH["❌ NO_MATCH"]

    style MATCH fill:#00b894,color:#fff,stroke:none
    style PARTIAL fill:#fdcb6e,color:#000,stroke:none
    style NOMATCH fill:#d63031,color:#fff,stroke:none
```

### Output JSON (Single Document)

```json
{
  "address_extraction": {
    "line1": "Flat 302, Sai Krupa Apartments, MG Road",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411001"
  }
}
```

---

## Feature 4: ID & Address Proof Check

**Goal:** Validate extracted fields (Aadhaar checksum, PAN format, Passport format), check that required proofs are present, and cross-match name/DOB/address across documents.

### What Triggers It

User includes `idproof` in features:
```bash
curl -X POST "http://localhost:8000/upload?features=idproof" -F "file=@data/aadhaar.jpg"
```

In `document_processor.py` → `run_idproof = features is None or "idproof" in features`

### End-to-End Flow (Single Document Field Validation)

```mermaid
sequenceDiagram
    autonumber
    participant DP as DocumentProcessor
    participant CLS as Classification Result
    participant VAL as validate_extracted_fields()

    DP->>CLS: Get doc_type + extracted_fields
    Note over CLS: doc_type = "aadhaar_card"<br/>fields = {aadhaar_number: "2345 6789 0123", date_of_birth: "15/03/1990", pincode: "400001"}
    
    DP->>VAL: validate_extracted_fields("aadhaar_card", fields)
    
    Note over VAL: For each field, run the mapped validator:<br/><br/>aadhaar_number → validate_aadhaar()<br/>  • Strip spaces: "234567890123"<br/>  • Is 12 digits? ✅<br/>  • Starts with 2-9? ✅ (starts with 2)<br/>  • Verhoeff checksum? ✅ or ❌<br/><br/>date_of_birth → validate_date()<br/>  • Parse DD/MM/YYYY? ✅<br/>  • Not in future? ✅<br/><br/>pincode → validate_pincode()<br/>  • 6 digits, starts 1-9? ✅

    VAL-->>DP: {valid: true/false, results: {field: {is_valid, reason}}}
```

### Field Validators

| Document Type | Field | Validator | What It Checks |
|--------------|-------|-----------|----------------|
| **Aadhaar** | `aadhaar_number` | `validate_aadhaar()` | 12 digits, starts 2-9, **Verhoeff checksum** (UIDAI algorithm) |
| **Aadhaar** | `date_of_birth` | `validate_date()` | DD/MM/YYYY format, not in future |
| **Aadhaar** | `pincode` | `validate_pincode()` | 6 digits, starts 1-9 |
| **PAN** | `pan_number` | `validate_pan()` | `ABCDE1234F` format, 4th char = valid holder type |
| **PAN** | `date_of_birth` | `validate_date()` | DD/MM/YYYY format, not in future |
| **Passport** | `passport_number` | `validate_passport()` | 1 letter + 7 digits (e.g., `L1234567`) |
| **Passport** | `date_of_birth/issue/expiry` | `validate_date()` | DD/MM/YYYY format, not in future |
| **Bank Statement** | `ifsc_code` | `validate_ifsc()` | 4 letters + 0 + 6 alphanumeric (e.g., `SBIN0001234`) |
| **Utility Bill** | `bill_date/due_date` | `validate_date()` | DD/MM/YYYY format |

### Cross-Document Proof Check (proof_check.py → generate_status)

When multiple documents are submitted, `generate_status(docs)` runs 6 checks and produces a **PASS / REVIEW / REJECT** verdict:

```mermaid
graph TB
    DOCS["📄 Processed Documents<br/>(Aadhaar + PAN + Utility Bill)"] --> GS["generate_status()"]
    
    GS --> C1["1️⃣ Required Proofs<br/>≥1 ID Proof present?<br/>≥1 Address Proof present?"]
    GS --> C2["2️⃣ Field Validation<br/>Aadhaar Checksum OK?<br/>PAN Format OK?<br/>Passport Format OK?"]
    GS --> C3["3️⃣ Name Match<br/>Cross-document<br/>name consistency"]
    GS --> C4["4️⃣ DOB Match<br/>Cross-document<br/>date consistency"]
    GS --> C5["5️⃣ Address Match<br/>Cross-document<br/>address consistency"]
    GS --> C6["6️⃣ Confidence<br/>Flag if classification<br/>confidence < 0.30"]

    C1 -->|Missing| REJ
    C2 -->|Invalid| REJ
    C3 -->|Mismatch| REV
    C4 -->|Mismatch| REV
    C5 -->|Mismatch| REV
    C6 -->|Low| REV
    
    C1 -->|OK| PASS2
    C2 -->|OK| PASS2
    C3 -->|OK| PASS2
    C4 -->|OK| PASS2
    C5 -->|OK| PASS2
    C6 -->|OK| PASS2

    REJ["🔴 REJECT<br/>Auto-reject"]
    REV["🟡 REVIEW<br/>Manual check needed"]
    PASS2["🟢 PASS<br/>Auto-approve"]

    style DOCS fill:#e94560,color:#fff,stroke:none
    style REJ fill:#d63031,color:#fff,stroke:none,stroke-width:2px
    style REV fill:#fdcb6e,color:#000,stroke:none,stroke-width:2px
    style PASS2 fill:#00b894,color:#fff,stroke:none,stroke-width:2px
```

### Proof Categories

| Document | ID Proof? | Address Proof? |
|----------|-----------|----------------|
| **Aadhaar Card** | ✅ | ✅ (both!) |
| **PAN Card** | ✅ | ❌ |
| **Passport** | ✅ | ✅ |
| **Utility Bill** | ❌ | ✅ |
| **Bank Statement** | ❌ | ✅ |

### Verdict Decision Logic

```
┌──────────────────────────────────────────────────┐
│              generate_status(docs)                │
│                                                  │
│  Missing ID/Address proof?     ──YES──→  REJECT  │
│  Invalid field (checksum)?     ──YES──→  REJECT  │
│  ─────────────────────────────────────────────── │
│  Name mismatch across docs?    ──YES──→  REVIEW  │
│  DOB mismatch across docs?     ──YES──→  REVIEW  │
│  Address mismatch across docs? ──YES──→  REVIEW  │
│  Low classification confidence?──YES──→  REVIEW  │
│  ─────────────────────────────────────────────── │
│  Everything OK?                ──YES──→  PASS    │
└──────────────────────────────────────────────────┘
```

### Output JSON

<<<<<<< HEAD
```json
{
  "status": "REVIEW",
  "reasons": ["Name mismatch: pan_card='rahul kumar' vs aadhaar_card='rahul k.'"],
  "proofs": {"met": true, "missing": []},
  "field_validation": [
    {"doc_type": "aadhaar_card", "valid": true, "results": {"aadhaar_number": {"is_valid": true, "reason": ""}}},
    {"doc_type": "pan_card", "valid": true, "results": {"pan_number": {"is_valid": true, "reason": ""}}}
  ],
  "name_check": {"consistent": false, "mismatches": ["Name mismatch: pan_card='rahul kumar' vs aadhaar_card='rahul k.'"]},
  "dob_check": {"consistent": true, "mismatches": []},
  "address_check": {"consistent": true, "issues": []}
}
=======
## Data Flow: Complete Request → Response

### Async Upload (Default)

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI /upload
    participant Disk as Temp File
    participant DB as PostgreSQL
    participant RD as Redis Queue
    participant W as Celery Worker
    participant DP as DocumentProcessor

    C->>API: POST /upload (file + features)
    API->>Disk: Stream file in 1 MB chunks
    API->>DB: INSERT Job (status=queued)
    API->>RD: Dispatch process_document_task
    API-->>C: { job_id, status: "queued", poll_url }

    Note over C: Client is free — no waiting

    RD->>W: Pick up task
    W->>DB: UPDATE status=processing, step=INITIALIZING
    W->>DP: process_document(file_path, features, progress_callback)

    loop Each pipeline stage
        DP->>W: progress_callback(stage)
        W->>DB: UPDATE step=stage
    end

    DP-->>W: Processing result dict
    W->>DB: UPDATE status=completed, result={...}
    W->>Disk: DELETE temp file

    C->>API: GET /jobs/{job_id}
    API->>DB: SELECT * FROM jobs WHERE id=job_id
    API-->>C: { status: "completed", result: {...} }
```

### Sync Upload (?sync=true)

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI /upload?sync=true
    participant DP as DocumentProcessor
    participant PRE as Preprocessor
    participant OCR as OCRPipeline
    participant CLS as Classifier
    participant STM as StampDetector
    participant MIO as MinIO

    C->>API: POST /upload?sync=true (file bytes)
    Note over API: Stream file to disk

    API->>DP: process_document(file_path, features)

    DP->>PRE: load_image() + detect_blur()
    PRE-->>DP: quality_info + preprocessed

    opt MinIO enabled
        DP->>MIO: Save original + preprocessed
    end

    DP->>OCR: run(image)
    OCR-->>DP: {text, blocks, bboxes}

    DP->>CLS: run(parsed_blocks)
    CLS-->>DP: {doc_type, confidence, fields}

    opt stamp/signature features requested
        DP->>STM: process(image, ocr_text)
        Note over STM: YOLO + E-Stamp + QR + Anomaly
        STM-->>DP: {stamps, signatures, estamp_info}
    end

    DP-->>API: Complete result dict
    API-->>C: Full JSON response (blocking)
>>>>>>> 07eb263e492d3dfeadd231b7bc3a77f94edacd44
```

---

## Combined Final Verdict

<<<<<<< HEAD
All 4 features combine to produce one final assessment:
=======
```mermaid
graph TB
    DP["DocumentProcessor"] --> OE["OCREngine<br/>(Single Instance)"]
    
    OE --> OP["OCRPipeline<br/>Main text extraction"]
    OE --> SP["StampDetectionPipeline<br/>E-stamp text analysis"]
    
    Note["⚡ PaddleOCR loaded ONCE<br/>Shared across pipelines<br/>Saves ~500MB memory"]

    style OE fill:#e94560,color:#fff,stroke:none,stroke-width:2px
    style Note fill:#2d3436,color:#dfe6e9,stroke:none
```

---

## Storage Architecture (MinIO)

```
documents/                          ← Bucket
└── {uuid}/                         ← Per-document folder
    ├── original/
    │   └── aadhaar_front.jpg       ← Uploaded file as-is
    └── preprocessed/
        └── aadhaar_front_preprocessed.png  ← After sharpening
```

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **API** | FastAPI 0.136.1 | REST endpoints, streaming uploads |
| **Validation** | Pydantic v2 | Request/response schema validation |
| **Task Queue** | Celery 5.6.3 + Redis 7.4.0 | Background document processing |
| **Database** | PostgreSQL + SQLAlchemy 2.0 | Job tracking, audit, result persistence |
| **OCR** | PaddleOCR 3.5 | Text extraction from images |
| **Object Detection** | YOLOv8 (Ultralytics 8.3) | Stamp & signature localization |
| **Deep Learning** | PyTorch 2.12 + Torchvision | YOLO model runtime |
| **PDF Parsing** | pypdfium2 | PDF page rendering |
| **QR Code** | OpenCV | QR detection & decoding |
| **Image Processing** | OpenCV + NumPy + Pillow | Blur detection, sharpening, cropping, ink analysis |
| **Object Storage** | MinIO | Original + preprocessed document images |
| **Field Validation** | Pure Python | Verhoeff checksum, regex, fuzzy matching |
| **HTTP Client** | Requests | E-stamp authority verification (optional) |

---

## Program Execution Flow — Stamp Detection

Below is the step-by-step program execution flow specifically for the stamp detection system when processing a document via the API or test scripts:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client / Test Script
    participant API as upload.py (POST /upload)
    participant DP as DocumentProcessor
    participant PDF as PDFParser (pypdfium2)
    participant PRE as Preprocessor (OpenCV)
    participant OCR as OCRPipeline (PaddleOCR)
    participant CLS as ClassificationPipeline
    participant SDP as StampDetectionPipeline
    participant DET as StampDetector (YOLOv8)
    participant ESC as EStampClassifier
    participant QR as QRProcessor

    Client->>API: Upload File (Image/PDF bytes)
    API->>DP: process_from_bytes(file_bytes, filename)
    Note over DP: Write bytes to temporary file

    alt File is PDF
        DP->>PDF: parse(pdf_path)
        PDF-->>DP: Rendered Page PNGs
        Note over DP: Loop through each page
    end

    DP->>PRE: Preprocessing (Grayscale + Laplacian Blur Check)
    PRE-->>DP: Preprocessed Image (Sharpened if blurry)

    DP->>OCR: Run OCR (PaddleOCR)
    OCR-->>DP: Extracted Text & Blocks

    DP->>CLS: Run Document Classification
    CLS-->>DP: Doc Type (Aadhaar/PAN/Passport...)

    DP->>SDP: process(image, ocr_text)
    
    rect rgb(26, 32, 53)
        note right of SDP: Stamp Detection Flow (Independent)
        SDP->>DET: detect(image, ocr_text)
        
        DET->>DET: Run YOLOv8 Model (best.pt)
        Note over DET: Detects physical 'stamps' and 'signatures'
        
        DET->>ESC: classify(image, ocr_text)
        Note over ESC: Checks Certificate regex, state names, stamp duty
        
        ESC->>QR: Decode QR
        QR-->>ESC: Decoded QR Data (matches certificate?)
        ESC-->>DET: E-Stamp Score (>= 50 is e-stamp)
        
        DET->>DET: Run Anomaly Checks on crops (Faded / Contrast / Blur)
        DET-->>SDP: Combined Stamp Detection Results
    end

    SDP-->>DP: Serializable JSON (stamps, signatures, anomalies, e-stamp details)
    
    alt File is PDF
        Note over DP: Aggregate results across all pages
    end

    DP-->>API: Full Processing Result Dict
    API-->>Client: Final JSON Response
```

### Flow Breakdown

1. **Upload / Trigger:** The client sends the raw file bytes via `POST /upload` or triggers a local file-based script run.
2. **Bytes Handoff:** `upload.py` reads raw bytes and forwards them to `DocumentProcessor.process_from_bytes()`.
3. **Format Check:**
   - **If PDF:** `PDFParser` renders pages as temporary PNGs. Each page is processed sequentially, and the final results are aggregated.
   - **If Image:** OpenCV loads the image directly.
4. **Image Preprocessing:** Checks for blur. If blurry, runs OpenCV sharpening (Unsharp Mask).
5. **OCR & Document Classification:** PaddleOCR extracts text blocks, which the `ClassificationPipeline` scores to identify the document type.
6. **Stamp Detection Core:**
   - **YOLOv8** localizes physical stamps and signatures.
   - **EStampClassifier** uses OCR regex rules and runs the **QRProcessor** (using OpenCV) to locate/decode QR codes. An e-stamp score >= 50 confirms it as an e-stamp.
   - **Anomaly Detector** flags any physical detections that are faded, blurry, or low-contrast.
7. **Aggregation & JSON Response:** Results are structured into a JSON response, removing non-serializable elements like numpy arrays, and returned to the client.

---

## Pipeline 6: Production Upload System (Async Processing)

### Why Was This Built?

The original `/upload` endpoint had 4 critical problems for real-world use:

| Problem | What Happened | Why It's Bad |
|---------|--------------|-------------|
| **Full file in RAM** | `await file.read()` loaded entire file into memory | A 100 MB PDF = 100 MB RAM instantly gone. Multiple uploads = server crash. |
| **Blocking event loop** | `processor.process_from_bytes()` ran synchronously | YOLO + PaddleOCR takes 30-300 seconds. During this time, NO other HTTP request could be served. |
| **No file size limit** | Anyone could upload a 2 GB file | Server would run out of memory and crash. |
| **No timeout handling** | 50-page PDF = 5+ minutes processing | HTTP request would timeout before results were ready. Client gets an error even though processing was working. |

### Architecture: Before vs After
>>>>>>> 07eb263e492d3dfeadd231b7bc3a77f94edacd44

```mermaid
graph LR
    subgraph "4 Feature Outputs"
        F1["🔵 Stamp Check<br/>E-stamp confirmed?<br/>Physical stamps found?<br/>Anomalies?"]
        F2["🔵 Signature Check<br/>Signatures present?<br/>Count & locations"]
        F3["🔵 Address Check<br/>Address extracted?<br/>Cross-doc match?"]
        F4["🔵 ID Proof Check<br/>Fields valid?<br/>Proofs present?<br/>Cross-doc consistent?"]
    end

    F1 --> VERDICT
    F2 --> VERDICT
    F3 --> VERDICT
    F4 --> VERDICT

    VERDICT{"generate_status()"}
    VERDICT -->|All OK| CLEAR["🟢 CLEAR<br/>Everything valid"]
    VERDICT -->|Soft issues| REVIEW["🟡 REVIEW<br/>Human review needed"]
    VERDICT -->|Hard failures| REJECT["🔴 REJECT<br/>Hard rule failed"]

    style CLEAR fill:#00b894,color:#fff,stroke:none
    style REVIEW fill:#fdcb6e,color:#000,stroke:none
    style REJECT fill:#d63031,color:#fff,stroke:none
```

| Verdict | Trigger | Example |
|---------|---------|---------|
| **🟢 CLEAR** | All proofs present + all fields valid + no mismatches | Aadhaar checksum OK, PAN format OK, names match, addresses match |
| **🟡 REVIEW** | Soft issues — data present but inconsistent | Name on PAN ≠ name on Aadhaar, or classification confidence < 30% |
| **🔴 REJECT** | Hard failures — missing or invalid data | Missing ID proof, Aadhaar checksum failed, invalid PAN format |

---

## How to Run the Full System

### Prerequisites

| Service | Required | Install |
|---------|----------|--------|
| **Python 3.10+** | ✅ | Already installed |
| **Redis** | ✅ | Installed manually on your machine |
| **PostgreSQL** | ✅ | Download from https://www.postgresql.org/download/windows/ |
| **MinIO** | Optional | Already in project (`minio.exe`) |

### Step 1: Create PostgreSQL Database

```bash
psql -U postgres -c "CREATE DATABASE intellicheck;"
```

Default connection string: `postgresql://postgres:postgres@localhost:5432/intellicheck`

> **Note:** Tables are auto-created when FastAPI starts — no manual schema setup needed.

### Step 2: Install Dependencies

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 3: Start All Services (3 Terminals)

```bash
# ── Terminal 1: Redis ──
redis-server

# ── Terminal 2: Celery Worker ──
.\venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

# ── Terminal 3: FastAPI ──
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Step 4: Upload & Check

```bash
# Async upload (returns job_id instantly)
curl -X POST http://localhost:8000/upload -F "file=@data/estamp2.pdf"
# → { "job_id": "abc-123", "status": "queued", "poll_url": "/jobs/abc-123" }

# Poll for results
curl http://localhost:8000/jobs/abc-123
# → { "status": "processing", "step": "OCR" }
# ... wait ...
# → { "status": "completed", "result": { ... full result ... } }

# Sync upload (blocks until done — for small files / testing)
curl -X POST "http://localhost:8000/upload?sync=true" -F "file=@data/sample.webp"

# Feature selection (only run specific checks)
curl -X POST "http://localhost:8000/upload?features=stamp,signature" -F "file=@data/agreement.jpg"
curl -X POST "http://localhost:8000/upload?features=address,idproof" -F "file=@data/aadhaar.jpg"

# List all completed jobs
curl "http://localhost:8000/jobs?status=completed&limit=10"
```

### Running Without Celery/Redis/PostgreSQL (Local Testing)

The existing CLI scripts still work without any infrastructure:

```bash
# These scripts directly call DocumentProcessor — no Celery/Redis/PG needed:
python scripts/run_document_pipeline.py data/estamp2.pdf --no-minio
python tests/stamp_detection/test_stamp_detector_simple.py
python tests/test_document_verification.py
```

### API Endpoints

| Method | Path | Purpose |
|--------|------|--------|
| `POST` | `/upload` | Upload document → returns `job_id` (async) |
| `POST` | `/upload?sync=true` | Upload document → returns result (blocking, for testing) |
| `POST` | `/upload?features=stamp,address` | Upload with specific feature selection |
| `GET` | `/jobs/{job_id}` | Poll job status + get result when completed |
| `GET` | `/jobs` | List recent jobs (filterable by status) |
| `POST` | `/classify` | Classify text without image upload |
| `GET` | `/` | Health check |
