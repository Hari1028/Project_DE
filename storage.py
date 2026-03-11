import os
import json
import csv
from datetime import datetime
from google.cloud import storage
from logger import logger
from config import COMPANY_FILE, WATERMARK_FILE, BUCKET_NAME

# Initialize the GCS client and connect to your specific bucket
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

def load_comp_libraries(): 
    """Reads the static seed list from the local environment."""
    libraries = []
    if not os.path.exists(COMPANY_FILE):
        logger.error(f"Missing {COMPANY_FILE}. Please create it.")
        return libraries

    with open(COMPANY_FILE, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            libraries.append(row)
    return libraries

def load_watermark():
    """Reads the pipeline's memory (state) directly from GCS."""
    blob = bucket.blob(WATERMARK_FILE)
    if blob.exists():
        data = blob.download_as_text()
        return json.loads(data)
    return {}

def save_watermark(state):
    """Saves the updated state back to GCS."""
    blob = bucket.blob(WATERMARK_FILE)
    blob.upload_from_string(
        data=json.dumps(state, indent=4),
        content_type='application/json'
    )
    logger.info("Watermark state successfully updated in GCS.")

def should_ingest(library_key, new_timestamp, watermark):
    if library_key not in watermark:
        return True
    return new_timestamp > watermark[library_key]

def save_to_gcs(folder, library, data):
    """
    Saves raw JSON directly to GCS matching the Bronze logical partitions: 
    bronze/{folder}/YYYY/MM/DD/library.json
    """
    today = datetime.utcnow()
    
    # Define the exact object path (the "blob name") inside the bucket
    gcs_path = f"bronze/{folder}/{today.year}/{today.month:02d}/{today.day:02d}/{library}.json"
    
    blob = bucket.blob(gcs_path)
    
    # Convert Python dictionary to a JSON string and upload directly to memory
    blob.upload_from_string(
        data=json.dumps(data, indent=4),
        content_type='application/json'
    )
        
    logger.info(f"Saved raw data to gs://{BUCKET_NAME}/{gcs_path}")