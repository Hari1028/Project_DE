from logger import logger
from api_client import get_resilient_session, fetch_dependencies
from storage import load_comp_libraries, load_watermark, save_watermark, should_ingest, save_to_gcs
from datetime import datetime

def run_pipeline():
    logger.info("=========================================")
    logger.info("Starting GCP cloud ingestion pipeline...")
    
    session = get_resilient_session()
    libraries = load_comp_libraries()
    watermark = load_watermark()
         
    for item in libraries: # iteration
        platform = item["platform"]
        library = item["library"]

        logger.info(f"--- Processing: {library} ---")

        # Process Dependency Data
        dependency_data = fetch_dependencies(session, platform, library)
        
        if dependency_data:
            updated_at = dependency_data.get("updated_at", "")
            if not updated_at:
                updated_at = datetime.utcnow().isoformat()
                
            dep_key = f"{library}_dependencies"
            
            if should_ingest(dep_key, updated_at, watermark):
                # The big swap: routing data to the cloud instead of local disk
                save_to_gcs("dependencies", library, dependency_data)
                watermark[dep_key] = updated_at
            else:
                logger.info(f"No dependency update for {library}")

    save_watermark(watermark)
    logger.info("Pipeline completed successfully!")

if __name__ == "__main__":
    run_pipeline()