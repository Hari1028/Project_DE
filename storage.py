import os
import json
import csv
from datetime import datetime
from logger import logger
from config import SEED_FILE, WATERMARK_FILE

def load_seed_libraries():
    libraries = []
    if not os.path.exists(SEED_FILE):
        logger.error(f"Missing {SEED_FILE}. Please create it.")
        return libraries

    with open(SEED_FILE, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            libraries.append(row)
    return libraries

def load_watermark():
    if os.path.exists(WATERMARK_FILE):
        with open(WATERMARK_FILE, "r") as f:
            return json.load(f)
    return {}

def save_watermark(state):
    with open(WATERMARK_FILE, "w") as f:
        json.dump(state, f, indent=4)

def should_ingest(library_key, new_timestamp, watermark):
    if library_key not in watermark:
        return True
    return new_timestamp > watermark[library_key]

def save_locally(folder, library, data):
    """
    Saves raw JSON to: bronze/{folder}/YYYY/MM/DD/library.json
    """
    today = datetime.utcnow()
    path_dir = f"bronze/{folder}/{today.year}/{today.month:02d}/{today.day:02d}"
    os.makedirs(path_dir, exist_ok=True)
    
    file_path = f"{path_dir}/{library}.json"
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
        
    logger.info(f"Saved raw data to {file_path}")