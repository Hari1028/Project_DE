from logger import logger
from api_client import get_resilient_session, fetch_project, fetch_dependencies
from storage import load_seed_libraries, load_watermark, save_watermark, should_ingest, save_locally
from datetime import datetime

def run_pipeline():
    logger.info("=========================================")
    logger.info("Starting local ingestion pipeline...")
    
    session = get_resilient_session()
    libraries = load_seed_libraries()
    watermark = load_watermark()

    for item in libraries:
        platform = item["platform"]
        library = item["library"]

        logger.info(f"--- Processing: {library} ---")

        # 1. PROCESS PROJECT DATA
        project_data = fetch_project(session, platform, library)
        if project_data:
            release_time = project_data.get("latest_release_published_at")
            if release_time:
                if should_ingest(library, release_time, watermark):
                    save_locally("projects", library, project_data)
                    watermark[library] = release_time
                else:
                    logger.info(f"No project update detected for {library}")

        # 2. PROCESS DEPENDENCY DATA
        dependency_data = fetch_dependencies(session, platform, library)
        if dependency_data:
            updated_at = dependency_data.get("updated_at", "")
            if not updated_at:
                updated_at = datetime.utcnow().isoformat()
                
            dep_key = f"{library}_dependencies"
            if should_ingest(dep_key, updated_at, watermark):
                save_locally("dependencies", library, dependency_data)
                watermark[dep_key] = updated_at
            else:
                logger.info(f"No dependency update for {library}")

    save_watermark(watermark)
    logger.info("Pipeline completed successfully!")

if __name__ == "__main__":
    run_pipeline()