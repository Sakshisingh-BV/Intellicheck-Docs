import logging
from minio import Minio

logger = logging.getLogger(__name__)

client = Minio(
    "127.0.0.1:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False,
)

bucket_name = "documents"

try:
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
except Exception as e:
    logger.warning(
        "MinIO not reachable at startup — bucket check skipped. "
        "Upload requests will fail until MinIO is available. Error: %s", e
    )