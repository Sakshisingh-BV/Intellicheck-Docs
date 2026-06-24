# Intellicheck — System Architecture

> Intelligent Document Verification Platform  
> OCR · Classification · Stamp Detection · Address Verification · ID Proof Validation

---

## System Overview

```mermaid
graph TB
    subgraph CLIEntryPoint
        CLI["scripts/run_document_pipeline.py\n━━━━━━━━━━━━━━━\nInput: data/ folder\nOutput: data/test_outputs/"]
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

    subgraph Output
        JSON["📋 JSON Result File\ndata/test_outputs/"]
        VIZ["🖼️ Detection Visualizations\nBounding Box PNGs"]
    end

    CLI --> DP
    DP --> PDF --> PRE
    DP --> PRE
    PRE --> OCR --> CLS
    DP --> STM
    PC --> FV
    PC --> AV
    DP --> JSON
    DP --> VIZ

    style DP fill:#1a1a2e,stroke:#e94560,color:#fff,stroke-width:2px
    style CLI fill:#e94560,color:#fff,stroke:none
    style OCR fill:#16213e,stroke:#0f3460,color:#fff
    style CLS fill:#16213e,stroke:#0f3460,color:#fff
    style STM fill:#16213e,stroke:#0f3460,color:#fff
    style PC fill:#0f3460,stroke:#e94560,color:#fff,stroke-width:2px
    style JSON fill:#0f3460,color:#fff,stroke:none
    style VIZ fill:#0f3460,color:#fff,stroke:none
```

---

## Module Map

```text
app/
├── core/
│   └── config.py                        ← Feature selection, progress stages
│
├── services/
│   └── document_processor.py            ← Central orchestrator (features + progress)
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
│   └── sign_detect/                     ← Alternative signature models
│
├── storage/                             ← Storage abstraction layer (placeholder)
└── utils/                               ← Shared utility functions (placeholder)

scripts/
└── run_document_pipeline.py             ← CLI entry point (main program)
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
        UP["📁 File Path\n(Image or PDF)"]
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

    subgraph OUTPUT
        RES["📋 JSON Result\ndata/test_outputs/"]
    end

    UP --> R
    R -->|Yes| PDF --> IMG
    R -->|No| IMG
    IMG --> BL
    BL -->|Blurry| SH --> OCR
    BL -->|Sharp| OCR
    OCR --> CL --> RES
    OCR --> ST --> RES

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

## Data Flow: Input → Output

```mermaid
sequenceDiagram
    participant User as User
    participant CLI as run_document_pipeline.py
    participant DP as DocumentProcessor
    participant PRE as Preprocessor
    participant OCR as OCRPipeline
    participant CLS as Classifier
    participant STM as StampDetector

    User->>CLI: python scripts/run_document_pipeline.py data/sample.webp

    CLI->>DP: process_document(file_path)

    DP->>PRE: load_image() + detect_blur()
    PRE-->>DP: quality_info + preprocessed

    DP->>OCR: run(image)
    OCR-->>DP: {text, blocks, bboxes}

    DP->>CLS: run(parsed_blocks)
    CLS-->>DP: {doc_type, confidence, fields}

    opt stamp/signature features enabled
        DP->>STM: process(image, ocr_text)
        Note over STM: YOLO + E-Stamp + QR + Anomaly
        STM-->>DP: {stamps, signatures, estamp_info}
    end

    DP-->>CLI: Complete result dict
    CLI->>CLI: Save JSON to data/test_outputs/
    CLI->>CLI: Save visualization PNGs
    CLI-->>User: Print result to console
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

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **OCR** | PaddleOCR 3.5 | Text extraction from images |
| **Object Detection** | YOLOv8 (Ultralytics 8.3) | Stamp & signature localization |
| **Deep Learning** | PyTorch 2.12 + Torchvision | YOLO model runtime |
| **PDF Parsing** | pypdfium2 | PDF page rendering |
| **QR Code** | OpenCV | QR detection & decoding |
| **Image Processing** | OpenCV + NumPy + Pillow | Blur detection, sharpening, cropping, ink analysis |
| **Field Validation** | Pure Python | Verhoeff checksum, regex, fuzzy matching |
| **HTTP Client** | Requests | E-stamp authority verification (optional) |

---

## Program Execution Flow — Stamp Detection

Below is the step-by-step program execution flow specifically for the stamp detection system when processing a document:

```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant CLI as run_document_pipeline.py
    participant DP as DocumentProcessor
    participant PDF as PDFParser (pypdfium2)
    participant PRE as Preprocessor (OpenCV)
    participant OCR as OCRPipeline (PaddleOCR)
    participant CLS as ClassificationPipeline
    participant SDP as StampDetectionPipeline
    participant DET as StampDetector (YOLOv8)
    participant ESC as EStampClassifier
    participant QR as QRProcessor

    User->>CLI: python scripts/run_document_pipeline.py data/estamp2.pdf
    CLI->>DP: process_document(file_path)

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

    DP-->>CLI: Full Processing Result Dict
    CLI->>CLI: Save JSON + Visualization PNGs
    CLI-->>User: Print result to console
```

### Flow Breakdown

1. **Input:** The user runs the CLI script with a file path from the `data/` folder.
2. **Format Check:**
   - **If PDF:** `PDFParser` renders pages as temporary PNGs. Each page is processed sequentially, and the final results are aggregated.
   - **If Image:** OpenCV loads the image directly.
3. **Image Preprocessing:** Checks for blur. If blurry, runs OpenCV sharpening (Unsharp Mask).
4. **OCR & Document Classification:** PaddleOCR extracts text blocks, which the `ClassificationPipeline` scores to identify the document type.
5. **Stamp Detection Core:**
   - **YOLOv8** localizes physical stamps and signatures.
   - **EStampClassifier** uses OCR regex rules and runs the **QRProcessor** (using OpenCV) to locate/decode QR codes. An e-stamp score >= 50 confirms it as an e-stamp.
   - **Anomaly Detector** flags any physical detections that are faded, blurry, or low-contrast.
6. **Output:** Results are saved as JSON to `data/test_outputs/` and visualization PNGs are saved alongside.

---

## How to Run

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Python 3.10+** | Tested on 3.10–3.12 |

### Install Dependencies

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run the Pipeline

```bash
# Process a PDF
python scripts/run_document_pipeline.py data/estamp2.pdf

# Process an image
python scripts/run_document_pipeline.py data/sample.webp

# Custom output path
python scripts/run_document_pipeline.py data/sample.webp -o data/test_outputs/custom_result.json
```

Output is automatically saved to `data/test_outputs/`.
