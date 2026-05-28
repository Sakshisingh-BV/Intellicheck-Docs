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

## 8. VS Code MinIO Extension

Install extension:

```text
AWS Toolkit
```

because MinIO is S3-compatible.

Connection values:

```text
Access Key: minioadmin
Secret Key: minioadmin
Endpoint: http://127.0.0.1:9000
Region: us-east-1
```

---
Note: minio.exe is not pushed to GitHub because GitHub blocks files larger than 100 MB.

## 9. Important About Git Push

