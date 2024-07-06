from google.cloud import storage
from config import Config

bucket_name = Config.GCLOUD_STORAGE_BUCKET

def upload_to_gcs(source_file_path, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_path)
    print(f"File {source_file_path} uploaded to {destination_blob_name}.")

def download_from_gcs(source_blob_name, destination_file_path):
    """Downloads a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    blob.download_to_filename(destination_file_path)
    print(f"Blob {source_blob_name} downloaded to {destination_file_path}.")