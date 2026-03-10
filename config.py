import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

API_KEY = os.getenv("LIBRARIES_API_KEY")
BASE_URL = "https://libraries.io/api"
SEED_FILE = "seed_libraries.csv"
WATERMARK_FILE = "watermark_state.json"
LOG_FILE = "pipeline_execution.txt"