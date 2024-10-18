from google.cloud import storage
import os
from google.oauth2 import service_account
import io
import config 

# --- Configure Google Cloud Storage ---
PROJECT_ID = config.PROJECT_ID
BUCKET_NAME = config.BUCKET_NAME
CREDENTIALS_PATH = <YOUR-CREDENTIALS-JSON>


def upload_file_to_gcs(file_bytes, filename): # More general function name
    """Uploads a file to Google Cloud Storage."""
    try:
        storage_client = storage.Client(project=PROJECT_ID)  # Let Google Cloud find credentials
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)

        # Upload from bytes, automatically detecting content type if possible
        blob.upload_from_string(file_bytes)  # No need to specify content_type manually

        return f"File '{filename}' uploaded successfully to GCS.", f"gs://{BUCKET_NAME}/{filename}"

    except Exception as e:
        return f"Error uploading file to GCS: {type(e).__name__} - {str(e)}", None