"""
Centralized application configuration.

All settings are configurable via environment variables with sensible defaults.
"""

import os

# ── Upload Settings ──────────────────────────────────────────────────────

MAX_UPLOAD_SIZE_BYTES = int(
    os.environ.get("MAX_UPLOAD_SIZE_MB", "100")
) * 1024 * 1024  # Default 100 MB

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf"
}

UPLOAD_TEMP_DIR = os.environ.get(
    "UPLOAD_TEMP_DIR",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "uploads",
    ),
)

# ── Redis ────────────────────────────────────────────────────────────────

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# ── PostgreSQL ───────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/intellicheck",
)

# ── Celery ───────────────────────────────────────────────────────────────

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
)

# ── Job Settings ─────────────────────────────────────────────────────────

JOB_RESULT_TTL_SECONDS = int(
    os.environ.get("JOB_RESULT_TTL_SECONDS", "86400")
)  # 24 hours in Redis

# ── Feature Selection ────────────────────────────────────────────────────

ALL_FEATURES = {"stamp", "signature", "address", "idproof"}
DEFAULT_FEATURES = ALL_FEATURES.copy()

# ── Progress Stages ──────────────────────────────────────────────────────

PROGRESS_STAGES = [
    "INITIALIZING",
    "PREPROCESSING",
    "OCR",
    "STAMP_DETECTION",
    "SIGNATURE_DETECTION",
    "ADDRESS_CHECK",
    "ID_PROOF_CHECK",
    "FINALIZING",
]

# ── MinIO ────────────────────────────────────────────────────────────────

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "127.0.0.1:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "documents")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
