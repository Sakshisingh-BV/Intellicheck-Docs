from minio import Minio

client = Minio(
    "127.0.0.1:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False,
)

bucket_name = "documents"

if not client.bucket_exists(bucket_name):
    client.make_bucket(bucket_name)