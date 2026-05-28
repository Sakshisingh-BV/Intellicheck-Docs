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

## 9. Important About Git Push

If MinIO extension is NOT pushed to GitHub:

NO ISSUE 👀

Extensions are installed locally on YOUR machine only.

They are usually stored somewhere like:

```text
C:\Users\<username>\.vscode\extensions
```

They are NOT part of your project folder.

So:

* GitHub pe push nahi hote
* repo clone karne pe automatically nahi aate
* har developer apni machine pe install karta hai

---

## 10. Important `.gitignore`

Create:

```text
.gitignore
```

Add:

```text
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
