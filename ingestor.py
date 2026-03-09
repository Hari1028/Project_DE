import requests
import json
import csv
import os
import logging
from datetime import datetime
from google.cloud import storage

# ---------------------------------------------------------
# CONFIGURATION SECTION
# ---------------------------------------------------------

# Libraries.io API key
API_KEY = "YOUR_API_KEY"

# Base URL
BASE_URL = "https://libraries.io/api"

# GCS bucket name
BUCKET_NAME = "oss-library-monitoring"

# Seed file containing libraries
SEED_FILE = "seed_libraries.csv"

# Watermark file (local for now)
WATERMARK_FILE = "watermark_state.json"

# Service account authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service_account.json"

# ---------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------------------------------------------------
# LOAD WATERMARK STATE
# ---------------------------------------------------------

def load_watermark():
    """
    Load previously stored watermark values.
    This helps track the last processed timestamp
    for each library.
    """
    if os.path.exists(WATERMARK_FILE):
        with open(WATERMARK_FILE, "r") as f:
            return json.load(f)
    return {}

# ---------------------------------------------------------
# SAVE WATERMARK STATE
# ---------------------------------------------------------

def save_watermark(state):
    """
    Save updated watermark state after ingestion.
    """
    with open(WATERMARK_FILE, "w") as f:
        json.dump(state, f, indent=4)

# ---------------------------------------------------------
# READ SEED LIBRARIES
# ---------------------------------------------------------

def load_seed_libraries():
    """
    Reads the seed library list from CSV.
    The file should contain columns:
    platform, library
    """
    libraries = []

    with open(SEED_FILE, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            libraries.append(row)

    return libraries

# ---------------------------------------------------------
# CALL PROJECT API
# ---------------------------------------------------------

def fetch_project(platform, library):
    """
    Fetch metadata about the library
    using the Project endpoint.
    """
    url = f"{BASE_URL}/{platform}/{library}?api_key={API_KEY}"

    response = requests.get(url)

    if response.status_code == 200:
        return response.json()

    logging.error(f"Failed to fetch project data for {library}")
    return None

# ---------------------------------------------------------
# CALL DEPENDENCIES API
# ---------------------------------------------------------

def fetch_dependencies(platform, library):
    """
    Fetch dependency information for the library.
    """
    url = f"{BASE_URL}/{platform}/{library}/dependencies?api_key={API_KEY}"

    response = requests.get(url)

    if response.status_code == 200:
        return response.json()

    logging.error(f"Failed to fetch dependencies for {library}")
    return None

# ---------------------------------------------------------
# UPLOAD DATA TO GCS BRONZE LAYER
# ---------------------------------------------------------

def upload_to_gcs(folder, library, data):
    """
    Upload raw JSON response to GCS Bronze storage.
    Files are partitioned by ingestion date.
    """

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    today = datetime.utcnow()

    # Date-based partition
    path = f"bronze/{folder}/{today.year}/{today.month}/{today.day}/{library}.json"

    blob = bucket.blob(path)

    blob.upload_from_string(
        json.dumps(data),
        content_type="application/json"
    )

    logging.info(f"Uploaded {library} data to {path}")

# ---------------------------------------------------------
# WATERMARK CHECK LOGIC
# ---------------------------------------------------------

def should_ingest(library, new_timestamp, watermark):
    """
    Determine whether new data should be ingested.
    """

    if library not in watermark:
        return True

    previous_timestamp = watermark[library]

    return new_timestamp > previous_timestamp

# ---------------------------------------------------------
# MAIN INGESTION PIPELINE
# ---------------------------------------------------------

def run_pipeline():

    logging.info("Starting ingestion pipeline")

    # Load seed libraries
    libraries = load_seed_libraries()

    # Load watermark state
    watermark = load_watermark()

    for item in libraries:

        platform = item["platform"]
        library = item["library"]

        logging.info(f"Processing library: {library}")

        # -------------------------------------------------
        # FETCH PROJECT DATA
        # -------------------------------------------------

        project_data = fetch_project(platform, library)

        if project_data:

            release_time = project_data.get("latest_release_published_at")

            if release_time:

                if should_ingest(library, release_time, watermark):

                    upload_to_gcs("projects", library, project_data)

                    watermark[library] = release_time

                else:
                    logging.info(f"No update detected for {library}")

        # -------------------------------------------------
        # FETCH DEPENDENCY DATA
        # -------------------------------------------------

        dependency_data = fetch_dependencies(platform, library)

        if dependency_data:

            updated_at = dependency_data.get("updated_at")

            if updated_at:

                key = f"{library}_dependencies"

                if should_ingest(key, updated_at, watermark):

                    upload_to_gcs("dependencies", library, dependency_data)

                    watermark[key] = updated_at

                else:
                    logging.info(f"No dependency update for {library}")

    # Save updated watermark
    save_watermark(watermark)

    logging.info("Pipeline completed successfully")

# ---------------------------------------------------------
# SCRIPT ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    run_pipeline()