# Intellicheck — System Architecture

> Intelligent Document Verification Platform  
> OCR · Classification · Stamp Detection · Address Verification · ID Proof Validation

---

## System Overview

```mermaid
graph TB
    subgraph APIGatewayFastAPI
        A1["POST /upload\nAsync Upload → job_id"]
        A1S["POST /upload?sync=true\nSync Processing"]
        A2["POST /classify\nText-only Classification"]
        A3["GET /jobs/{id}\nPoll Job Status"]
        A4["GET /jobs\nList All Jobs"]
        A5["GET /\nHealth Check"]
    end

    subgraph BackgroundProcessing
        RD[("Redis\nMessage Queue")]
        CW["Celery Worker\n━━━━━━━━━━━━━━━\nLazy-loads models once\nProcesses documents"]
    end

    subgraph OrchestrationLayer
        DP["DocumentProcessor\n━━━━━━━━━━━━━━━\nCentral Brain\nManages all pipelines"]
    end

    subgraph InputHandling
        PDF["PDFParser\npypdfium2\nPDF → Page Images"]
        PRE["Preprocessor\nBlur Detection\nImage Sharpening"]
    end

    subgraph AnalysisPipelines
        direction TB
        OCR["OCR Pipeline\n━━━━━━━━━━━━\nPaddleOCR 3.5\nText Extraction"]
        CLS["Classification\n━━━━━━━━━━━━\nRule-Based Scoring\n5 Document Types"]
        STM["Stamp Detection\n━━━━━━━━━━━━\nYOLOv8 + E-Stamp\nQR + Anomaly"]
    end

    subgraph VerificationEngine
        direction TB
        FV["Field Validators\nAadhaar · PAN · Passport\nVerhoeff Checksum"]
        AV["Address Verification\nExtract · Normalize\nFuzzy Match"]
        PC["Proof Check\nCross-Document\nPASS / REVIEW / REJECT"]
    end

    subgraph Storage
        MIO["MinIO Object Store\nOriginal + Preprocessed"]
        PG[("PostgreSQL\nJob Tracking + Audit")]
    end

    A1 -->|"Stream to disk"| RD
    A1 -->|"Create job row"| PG
    A1S --> DP
    A2 --> CLS
    A3 --> PG
    A4 --> PG
    RD --> CW --> DP
    CW -->|"Update progress"| PG
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
```

---

## Module Map

```text
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
```

---

## Pipeline 1: Document Processing (End-to-End)

```mermaid
graph LR
    subgraph INPUT
        UP["📁 File Upload\n(Image or PDF)"]
    end

    subgraph PARSE
        R{"PDF?"}
        PDF["Render Pages\n75 DPI → PNG"]
        IMG["Load Image\nBGR numpy"]
    end

    subgraph PREPROCESS
        BL["Blur Detection\n3×3 grid Laplacian"]
        SH["Sharpen\nUnsharp Mask"]
    end

    subgraph EXTRACT
        OCR["PaddleOCR 3.5\nText + Bounding Boxes"]
    end

    subgraph ANALYZE
        CL["Classification\nKeyword Scoring"]
        ST["Stamp Detection\nYOLO + E-Stamp"]
    end

    subgraph STORE
        MI["MinIO\nSave originals"]
    end

    subgraph OUTPUT
        RES["📋 JSON Response"]
    end

    UP --> R
    R -->|Yes| PDF --> IMG
    R -->|No| IMG
    IMG --> BL
    BL -->|Blurry| SH --> OCR
    BL -->|Sharp| OCR
    OCR --> CL --> RES
    OCR --> ST --> RES
    IMG --> MI

    style UP fill:#e94560,color:#fff,stroke:none
    style RES fill:#0f3460,color:#fff,stroke:none
```

### PDF Multi-Page Handling

```mermaid
graph TB
    PDF["📄 Multi-page PDF"] --> RENDER["pypdfium2\nRender each page"]
    RENDER --> P1["Page 1 PNG"]
    RENDER --> P2["Page 2 PNG"]
    RENDER --> P3["Page N PNG"]
    
    P1 --> PROC1["Full Pipeline\nOCR → Classify → Stamp"]
    P2 --> PROC2["Full Pipeline\nOCR → Classify → Stamp"]
    P3 --> PROC3["Full Pipeline\nOCR → Classify → Stamp"]
    
    PROC1 --> AGG["Aggregate Results"]
    PROC2 --> AGG
    PROC3 --> AGG
    
    AGG --> R1["OCR: Merge all text"]
    AGG --> R2["Classification: Best confidence page wins"]
    AGG --> R3["Stamps: Union all bounding boxes"]

    style PDF fill:#e94560,color:#fff,stroke:none
    style AGG fill:#0f3460,color:#fff,stroke:none
```

---

## Pipeline 2: OCR + Classification

```mermaid
graph TB
    subgraph OCRPipeline
        I["Image"] --> ENG["OCREngine\nPaddleOCR 3.5\npredict()"]
        ENG --> PAR["OCRParser\nExtract: texts, scores, polygons"]
        PAR --> FMT["OCRFormatter\nJoin text blocks"]
        FMT --> OUT1["{ text, total_blocks, results[] }"]
    end

    subgraph ClassificationPipeline
        OUT1 --> CONCAT["Concatenate\nall text blocks"]
        CONCAT --> SCORE["Score against\n5 document rules"]
        SCORE --> WIN["Pick highest\nscoring type"]
        WIN --> REGEX["Extract fields\nvia regex patterns"]
        REGEX --> OUT2["ClassificationResult"]
    end

    style I fill:#e94560,color:#fff,stroke:none
    style OUT2 fill:#0f3460,color:#fff,stroke:none
```

### Classification: Document Types & Scoring

```mermaid
graph LR
    TXT["OCR Text"] --> S1["Aadhaar\nScore: 0.78"]
    TXT --> S2["PAN\nScore: 0.12"]
    TXT --> S3["Passport\nScore: 0.05"]
    TXT --> S4["Utility Bill\nScore: 0.02"]
    TXT --> S5["Bank Statement\nScore: 0.01"]
    
    S1 --> W["🏆 Winner:\naadhaar_card"]
    
    style W fill:#0f3460,color:#fff,stroke:none
    style S1 fill:#e94560,color:#fff,stroke:none
```

| Document | Category | Primary Keywords | Extracted Fields |
|---|---|---|---|
| **Aadhaar Card** | ID + Address | `aadhaar`, `uidai` | aadhaar_number, DOB, gender, pincode |
| **PAN Card** | ID only | `permanent account number` | pan_number, DOB |
| **Passport** | ID + Address | `passport`, `republic of india` | passport_number, DOB, issue/expiry dates |
| **Utility Bill** | Address only | `electricity bill`, `consumer number` | consumer_number, bill_date, amount |
| **Bank Statement** | Address only | `bank statement`, `ifsc` | account_number, ifsc_code, period |

### Scoring Weights

| Keyword Tier | Weight | Purpose |
|---|---|---|
| **Primary** | +3.0 | Strong identity signals (`aadhaar`, `passport`) |
| **Secondary** | +2.0 | Supporting context (`government of india`) |
| **Field Hints** | +1.0 | Weak signals (`dob`, `male`, `s/o`) |
| **Negative** | −2.0 | Disambiguation (`income tax` on Aadhaar = penalty) |

> **Confidence** = matched_score / max_possible_score  
> Below **0.15** → classified as `unknown`

---

## Pipeline 3: Stamp Detection

```mermaid
graph TB
    IMG["🖼️ Input Image"] --> DET["StampDetector.detect()"]
    
    DET --> YOLO
    DET --> ESTAMP
    DET --> ANOM
    
    subgraph PhysicalDetectionYOLO
        YOLO["YOLOv8 Model\n(best.pt)"] --> PARSE2["Parse Boxes\nconf ≥ 0.5"]
        PARSE2 --> CROP["Crop Each\nDetection"]
        CROP --> INK["Ink Check\n(HSV Saturation)"]
        INK --> DETS["Detections[]\nstamp / signature"]
    end

    subgraph EStampClassification
        ESTAMP["EStampClassifier"] --> EOCR["OCR Text\n(reused from pipeline)"]
        ESTAMP --> QR["QR Processor\nOpenCV QR Code"]
        EOCR --> ESCORE["Weighted Scoring\ncert=40, duty=25, state=15"]
        QR --> ESCORE
        ESCORE --> EDEC{"Score ≥ 50?"}
        EDEC -->|Yes| ET["✅ e_stamp"]
        EDEC -->|No| NT["❌ non_e_stamp"]
    end

    subgraph QualityChecks
        ANOM["AnomalyDetector"] --> F1["Faded? (std &lt; 30)"]
        ANOM --> F2["Low Contrast? (range &lt; 50)"]
        ANOM --> F3["Blurry? (Laplacian &lt; 100)"]
    end

    DETS --> RESULT["📋 Final Result"]
    ET --> RESULT
    NT --> RESULT
    F1 --> RESULT
    F2 --> RESULT
    F3 --> RESULT

    style IMG fill:#e94560,color:#fff,stroke:none
    style RESULT fill:#0f3460,color:#fff,stroke:none
    style ET fill:#00b894,color:#fff,stroke:none
    style NT fill:#636e72,color:#fff,stroke:none
```

### E-Stamp Scoring Breakdown

| Signal | Points | Detection Method |
|---|---|---|
| Certificate Number | **40** | Regex: `IN-MH12345678901234` |
| Stamp Duty Amount | **25** | Regex: `Rs. 100` (needs context) |
| State Name | **15** | Match against 22 Indian states |
| Date | **10** | Multiple date formats |
| QR Decoded (data) | **5** | OpenCV QRCodeDetector |
| QR Present (visual) | **2** | Contour-based detection / detect() |
| **Threshold** | **50** | Score ≥ 50 → e-stamp confirmed |

> **Context-aware:** Stamp duty, state, and date only count if a certificate number OR e-stamp keyword was already found. Prevents false positives from generic invoices.

### QR Code Detection & Decoding Flow

The `QRProcessor` (`app/stamp_detection/qr_processor.py`) implements a streamlined QR code detection and decoding workflow designed specifically for standard QR codes using OpenCV. It avoids external barcode or DataMatrix libraries (like pylibdmtx or pyzbar) and progressive cropping loops.

```mermaid
graph TD
    Start["📥 Input Image"] --> Gray["Grayscale Conversion"]
    Gray --> Decode{"1. Try OpenCV QR Decode\n(detectAndDecode)"}
    
    Decode -->|Success| Success["✅ Return QR Data\n(qr_present=True, qr_decoded=True)"]
    Decode -->|Failed| Visual{"2. QR Presence Check"}
    
    Visual -->|"Nested Contours / detect check"| Found{"QR Present?"}
    Found -->|Yes| Flag["⚠️ QR Detected visually but Decode Failed\n(qr_present=True, qr_decoded=False)"]
    Found -->|No| None["❌ No QR Code Found\n(qr_present=False, qr_decoded=False)"]

    style Start fill:#1a1a2e,stroke:#e94560,color:#fff
    style Success fill:#00b894,color:#fff
    style Flag fill:#fdcb6e,color:#000
    style None fill:#d63031,color:#fff
```

#### Detailed Decoding Priority
OpenCV's `cv2.QRCodeDetector` acts as the single unified engine for both QR presence detection and payload decoding.

#### OpenCV QR Presence Logic Check
To identify the presence of a QR code even when it is too blurry or distorted to decode, the processor performs a two-layered check:
1. **Contour-Based Finder Pattern Search:**
   It uses adaptive thresholding and hierarchical contour scanning to locate nested square-like structures (the typical finder patterns located at three corners of a standard QR code). If at least 2 candidate finder patterns are located, the QR presence flag is raised.
2. **OpenCV built-in detect Check:**
   If contour analysis fails, a direct fallback to `cv2.QRCodeDetector().detect()` is performed to double check if a QR code boundary is recognized.

---

## Pipeline 4: Address Verification

```mermaid
graph TB
    subgraph Step1Extract
        OCR2["OCR Text"] --> EXT["AddressExtractor"]
        EXT --> PIN["Pincode\n6-digit regex"]
        EXT --> STATE["State\n32 states list"]
        EXT --> CITY["City\n45+ cities list"]
        EXT --> LINE["Address Line\nBefore pincode / labeled"]
    end

    subgraph Step2Normalize
        PIN --> NORM["AddressNormalizer"]
        STATE --> NORM
        CITY --> NORM
        LINE --> NORM
        NORM --> N1["M.G. Rd. → Mahatma Gandhi Road"]
        NORM --> N2["Apt. → Apartment"]
        NORM --> N3["lowercase + clean"]
    end

    subgraph Step3Match
        N1 --> MAT["AddressMatcher"]
        N2 --> MAT
        N3 --> MAT
        MAT --> P1["Pincode: Exact"]
        MAT --> P2["State: Exact"]
        MAT --> P3["City: Fuzzy (≥0.85)"]
        MAT --> P4["Line1: Fuzzy + Containment"]
    end

    subgraph Step4Decision
        P1 --> DEC{"All Match?"}
        P2 --> DEC
        P3 --> DEC
        P4 --> DEC
        DEC -->|pin+state+3| MATCH["✅ MATCH"]
        DEC -->|pin+state only| PARTIAL["⚠️ PARTIAL_MATCH"]
        DEC -->|fail| NOMATCH["❌ NO_MATCH"]
    end

    style OCR2 fill:#e94560,color:#fff,stroke:none
    style MATCH fill:#00b894,color:#fff,stroke:none
    style PARTIAL fill:#fdcb6e,color:#000,stroke:none
    style NOMATCH fill:#d63031,color:#fff,stroke:none
```

### Freshness Rules

| Document Type | Maximum Age | Notes |
|---|---|---|
| Utility Bill | 90 days | Electricity, water, gas, phone |
| Bank Statement | 90 days | Account statement |
| Rental Agreement | 180 days | Lease agreement |
| Aadhaar / Passport / DL | 10 years | Government-issued IDs |

---

## Pipeline 5: ID Proof Validation & Final Verdict

```mermaid
graph TB
    DOCS["📄 Processed Documents\n(Aadhaar + PAN + Utility Bill)"] --> GS["generate_status()"]
    
    GS --> C1["1️⃣ Required Proofs\n≥1 ID Proof\n≥1 Address Proof"]
    GS --> C2["2️⃣ Field Validation\nAadhaar Checksum\nPAN Format\nPassport Format"]
    GS --> C3["3️⃣ Name Match\nCross-document\nname consistency"]
    GS --> C4["4️⃣ DOB Match\nCross-document\ndate consistency"]
    GS --> C5["5️⃣ Address Match\nCross-document\naddress consistency"]
    GS --> C6["6️⃣ Confidence\nFlag if\n&lt; 0.30"]

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

    REJ["🔴 REJECT\nAuto-reject"]
    REV["🟡 REVIEW\nManual check"]
    PASS2["🟢 PASS\nAuto-approve"]

    style DOCS fill:#e94560,color:#fff,stroke:none
    style REJ fill:#d63031,color:#fff,stroke:none,stroke-width:2px
    style REV fill:#fdcb6e,color:#000,stroke:none,stroke-width:2px
    style PASS2 fill:#00b894,color:#fff,stroke:none,stroke-width:2px
```

### Proof Categories

```mermaid
graph LR
    subgraph IDProofTypes
        I1["Aadhaar Card"]
        I2["PAN Card"]
        I3["Passport"]
    end

    subgraph AddressProofTypes
        A1["Aadhaar Card"]
        A2["Passport"]
        A3["Utility Bill"]
        A4["Bank Statement"]
    end

    I1 -.->|"Counts as both"| A1

    style I1 fill:#6c5ce7,color:#fff,stroke:none
    style A1 fill:#6c5ce7,color:#fff,stroke:none
```

> **Aadhaar** is the only document that counts as **both** ID proof and Address proof.

### Field Validators

| Validator | Format | Special Check |
|---|---|---|
| **Aadhaar** | 12 digits, starts 2-9 | **Verhoeff checksum** (UIDAI algorithm) |
| **PAN** | `ABCDE1234F` | 4th char must be valid holder type |
| **Passport** | `A1234567` | 1 letter + 7 digits |
| **Pincode** | 6 digits | Starts with 1-9 |
| **IFSC** | `XXXX0XXXXXX` | 4 letters + 0 + 6 alphanumeric |
| **Date** | `DD/MM/YYYY` | Must not be in future |

### Verdict Decision Tree

```text
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

---

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
```

---

## Shared Resource: OCR Engine

```mermaid
graph TB
    DP["DocumentProcessor"] --> OE["OCREngine\n(Single Instance)"]
    
    OE --> OP["OCRPipeline\nMain text extraction"]
    OE --> SP["StampDetectionPipeline\nE-stamp text analysis"]
    
    Note["⚡ PaddleOCR loaded ONCE\nShared across pipelines\nSaves ~500MB memory"]

    style OE fill:#e94560,color:#fff,stroke:none,stroke-width:2px
    style Note fill:#2d3436,color:#dfe6e9,stroke:none
```

---

## Storage Architecture (MinIO)

```text
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

```mermaid
graph LR
    subgraph BEFOREBlocking
        C1["Client"] -->|"POST /upload\n(waits 30-300 sec)"| API1["FastAPI\nfile.read() → RAM"]
        API1 -->|"Blocks entire server"| DP1["DocumentProcessor"]
        DP1 -->|"Response after processing"| C1
    end
```

```mermaid
graph TB
    subgraph AFTERAsyncwithBackgroundWorkers
        C2["Client"] -->|"POST /upload"| API2["FastAPI\nStream → Disk"]
        API2 -->|"Instant response\njob_id + status=queued"| C2
        API2 -->|"Create Job row"| PG[("PostgreSQL\njobs table")]
        API2 -->|"Dispatch task"| RD[("Redis\nMessage Queue")]
        RD --> W["Celery Worker\nLoads YOLO+PaddleOCR once\nProcesses documents"]
        W -->|"Update progress\nPREPROCESSING → OCR → ..."| PG
        W -->|"Save final result"| PG
        C2 -->|"GET /jobs/{id}\nPoll for status"| PG
    end

    style PG fill:#0f3460,color:#fff,stroke:none
    style RD fill:#e94560,color:#fff,stroke:none
    style W fill:#16213e,stroke:#0f3460,color:#fff
```

### Upload Flow: Step by Step

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI /upload
    participant Disk as Temp File (data/uploads/)
    participant DB as PostgreSQL (jobs table)
    participant Redis as Redis Queue
    participant Worker as Celery Worker
    participant DP as DocumentProcessor

    Client->>API: POST /upload (file + features)
    
    Note over API: Validate extension (.pdf, .jpg, etc.)
    
    API->>Disk: Stream file in 1 MB chunks
    Note over API,Disk: Check size during streaming\nAbort at 100 MB limit
    
    API->>DB: INSERT Job (status=queued)
    API->>Redis: Dispatch process_document_task
    API-->>Client: { job_id, status: "queued", poll_url }
    
    Note over Client: Client is FREE — no waiting
    
    Redis->>Worker: Pick up task
    Worker->>DB: UPDATE status=processing, step=INITIALIZING
    Worker->>DP: process_document(file_path, features)
    
    loop Each processing stage
        DP->>Worker: progress_callback("PREPROCESSING")
        Worker->>DB: UPDATE step=PREPROCESSING
        DP->>Worker: progress_callback("OCR")
        Worker->>DB: UPDATE step=OCR
        DP->>Worker: progress_callback("STAMP_DETECTION")
        Worker->>DB: UPDATE step=STAMP_DETECTION
    end
    
    DP-->>Worker: Processing result dict
    Worker->>DB: UPDATE status=completed, result={...}
    Worker->>Disk: DELETE temp file (try/finally cleanup)
    
    Client->>API: GET /jobs/{job_id}
    API->>DB: SELECT * FROM jobs WHERE id=job_id
    API-->>Client: { status: "completed", result: {...} }
```

### Design Decisions & Reasoning

#### 1. Stream to Disk, Not RAM

**What:** File is written to `data/uploads/` in 1 MB chunks during upload, never fully loaded into memory.

**Why:** A 100 MB scanned PDF loaded via `await file.read()` would instantly consume 100 MB of server RAM. With 5 concurrent uploads, that's 500 MB just for file storage — before any processing starts. Streaming to disk means the server only ever holds 1 MB in memory per upload, regardless of file size.

```python
# OLD — entire file in RAM:
file_data = await file.read()  # 100 MB PDF = 100 MB RAM

# NEW — stream to disk in chunks:
while True:
    chunk = await file.read(1_048_576)  # 1 MB at a time
    if not chunk:
        break
    if total_size > MAX_UPLOAD_SIZE_BYTES:  # Check DURING streaming
        raise HTTPException(413, "File too large")
    tmp.write(chunk)
```

#### 2. 100 MB File Size Limit

**What:** Size is checked during streaming — if the file exceeds 100 MB, upload is aborted immediately (partial file deleted).

**Why:** Without a limit, a malicious or accidental 2 GB upload would crash the server. The limit is checked **during** streaming, not after — so a 500 MB file is rejected after the first 100 MB, not after uploading all 500 MB.

#### 3. Celery + Redis for Background Processing

**What:** Upload returns instantly with a `job_id`. The actual processing happens in a separate Celery worker process.

**Why:** Document processing (PaddleOCR + YOLOv8) takes 30-300 seconds. If this runs inside the FastAPI request handler:
- The HTTP request blocks for the entire duration
- No other requests can be processed (Python GIL + synchronous processing)
- Client-side timeouts often kill the connection before processing finishes

With Celery, the FastAPI server stays responsive — it just creates a job record and returns. The heavy ML processing happens in a separate worker process.

#### 4. PostgreSQL for Job Storage (Not Just Redis)

**What:** Job status, progress, and final results are stored in PostgreSQL. Redis is only used as the Celery message queue.

**Why:**
- **Audit trail:** PostgreSQL keeps a permanent record of every document processed — when, what type, what result. This is required for KYC compliance.
- **Reliability:** Redis data can be lost on restart (it's in-memory). PostgreSQL persists to disk.
- **Query capability:** `GET /jobs?status=failed&limit=10` — you can filter, paginate, and search job history. Redis is not designed for this.

#### 5. Lazy Model Loading in Workers

**What:** PaddleOCR and YOLOv8 are loaded **once** when the first task runs, not on every task.

**Why:** Loading PaddleOCR takes ~5 seconds and uses ~500 MB RAM. Loading YOLOv8 takes ~2 seconds. If we loaded them per-task, every document would have a 7-second overhead. With lazy loading, the models are loaded once and reused for all subsequent tasks.

```python
_processor = None  # Module-level singleton

def _get_processor(use_minio=False):
    global _processor
    if _processor is None:  # Only loads models on FIRST call
        _processor = DocumentProcessor(use_minio=use_minio)
    return _processor
```

#### 6. Feature Selection

**What:** Clients can specify which analysis steps to run via `?features=stamp,address`.

**Why:** Not every use case needs all checks. If you only need to verify an address, running YOLO stamp detection wastes 10+ seconds. Feature selection lets the client skip unnecessary steps:

| Feature | What It Runs | Time Saved If Skipped |
|---------|-------------|----------------------|
| `stamp` | YOLOv8 + E-stamp classifier + anomaly detection | ~10-15 sec |
| `signature` | Same YOLO pass as stamp (detects both) | ~10-15 sec |
| `address` | Address extraction from OCR text | ~1 sec |
| `idproof` | Field validation (Aadhaar checksum, PAN format) | ~0.5 sec |

> OCR and Classification **always run** — they are required by all other features.

#### 7. Progress Stages

**What:** The worker reports its current stage to PostgreSQL as it processes:

```
INITIALIZING → PREPROCESSING → OCR → STAMP_DETECTION →
SIGNATURE_DETECTION → ADDRESS_CHECK → ID_PROOF_CHECK → FINALIZING
```

**Why:** When processing a 50-page PDF (which can take 5+ minutes), the client needs to know if the job is still running or stuck. Without progress reporting, the client can only see "processing" and has no idea if it will take 10 more seconds or 5 more minutes.

#### 8. `task_acks_late = True` + `task_reject_on_worker_lost = True`

**What:** Celery only acknowledges a task AFTER it completes. If a worker crashes mid-processing, the task is automatically re-queued.

**Why:** Without this, if a worker runs out of memory during YOLO inference and crashes, the task is marked as "acknowledged" (started) and never retried. The job would be stuck in "processing" forever. With late acknowledgment, crashed tasks are automatically picked up by another worker.

#### 9. `worker_prefetch_multiplier = 1`

**What:** Each Celery worker only grabs 1 task at a time from the queue.

**Why:** Document processing is CPU/GPU-heavy. If a worker prefetches 4 tasks but can only process 1 at a time, the other 3 sit idle in that worker's local buffer — even if other workers are free. With `prefetch_multiplier=1`, tasks are distributed fairly across all available workers.

#### 10. `?sync=true` Backward Compatibility

**What:** Adding `?sync=true` to the upload request makes it behave like the old blocking API — processes immediately and returns the full result.

**Why:** Existing test scripts and local development workflows rely on the immediate response. The sync mode preserves this behavior without requiring any changes to existing code.

### API Endpoints (Updated)

| Method | Path | Purpose |
|--------|------|--------|
| `POST` | `/upload` | Upload document → returns `job_id` (async) |
| `POST` | `/upload?sync=true` | Upload document → returns result (blocking, for testing) |
| `POST` | `/upload?features=stamp,address` | Upload with specific feature selection |
| `GET` | `/jobs/{job_id}` | Poll job status + get result when completed |
| `GET` | `/jobs` | List recent jobs (filterable by status) |
| `POST` | `/classify` | Classify text without image upload |
| `GET` | `/` | Health check |

### Job Lifecycle in PostgreSQL

```mermaid
stateDiagram-v2
    [*] --> queued : POST /upload
    queued --> processing : Celery worker picks up task
    
    state processing {
        INITIALIZING --> PREPROCESSING
        PREPROCESSING --> OCR
        OCR --> STAMP_DETECTION
        STAMP_DETECTION --> SIGNATURE_DETECTION
        SIGNATURE_DETECTION --> ADDRESS_CHECK
        ADDRESS_CHECK --> ID_PROOF_CHECK
        ID_PROOF_CHECK --> FINALIZING
    }
    
    processing --> completed : All steps successful
    processing --> failed : Exception thrown
    completed --> [*]
    failed --> [*]
```

### Celery Worker Configuration

| Setting | Value | Reason |
|---------|-------|--------|
| `worker_prefetch_multiplier` | 1 | Fair task distribution (1 task at a time) |
| `task_acks_late` | True | Acknowledge after completion (crash recovery) |
| `task_reject_on_worker_lost` | True | Re-queue task if worker crashes |
| `task_time_limit` | 600 sec | Hard kill after 10 minutes (prevent stuck tasks) |
| `task_soft_time_limit` | 540 sec | Graceful timeout at 9 minutes |
| `worker_max_memory_per_child` | 2 GB | Restart worker if memory exceeds 2 GB |
| `concurrency` | 2 | 2 parallel workers (each uses ~1.5 GB for ML models) |

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

To use a different connection, set environment variable:
```bash
set DATABASE_URL=postgresql://user:password@host:5432/dbname
```

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

### Step 4 (Optional): Start MinIO

```bash
# ── Terminal 4: MinIO (only needed if you want document storage) ──
.\minio.exe server minio-data
```

### Step 5: Open Swagger UI

Open in browser: **http://127.0.0.1:8000/docs**

### Usage Examples

```bash
# Async upload (large files — returns job_id instantly)
curl -X POST http://localhost:8000/upload -F "file=@data/estamp2.pdf"
# Response: { "job_id": "abc-123", "status": "queued", "poll_url": "/jobs/abc-123" }

# Poll for results
curl http://localhost:8000/jobs/abc-123
# Response: { "status": "processing", "step": "OCR" }
# ... wait ...
# Response: { "status": "completed", "result": { ... full result ... } }

# Sync upload (small files / testing — blocks until done)
curl -X POST "http://localhost:8000/upload?sync=true" -F "file=@data/sample.webp"

# Feature selection (only run specific checks)
curl -X POST "http://localhost:8000/upload?features=stamp,signature" -F "file=@data/sample.webp"
curl -X POST "http://localhost:8000/upload?features=address,idproof" -F "file=@data/aadhaar.jpg"

# List all completed jobs
curl "http://localhost:8000/jobs?status=completed&limit=10"
```

### Running Without Celery/Redis/PostgreSQL (Local Testing)

The existing CLI scripts still work without any of the new infrastructure:

```bash
# These scripts directly call DocumentProcessor — no Celery/Redis/PG needed:
python scripts/run_document_pipeline.py data/estamp2.pdf --no-minio
python tests/stamp_detection/test_stamp_detector_simple.py
python tests/test_document_verification.py
```

The `?sync=true` API mode also works without Celery (but still needs PostgreSQL for the FastAPI startup table check — this can be skipped if PG is not running, a warning is logged but the server still starts).

