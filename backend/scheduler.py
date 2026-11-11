import sys
import logging
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from database import SessionLocal
from services.firms_service import FIRMSService
from services.meteo_service import MeteoService

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PipelineScheduler")


def run_firms_job():
    """Job function triggered every 30 seconds to fetch and upsert NASA FIRMS hotspots via FIRMSService."""
    logger.info("--- [JOB START] NASA FIRMS Service ---")
    session = SessionLocal()
    try:
        firms_service = FIRMSService(session)
        # Service handles loading regions, API fetching, spatial matching, and upserting into DB
        count = firms_service.run_ingestion(
            day_range=1,
            source="VIIRS_SNPP_NRT"
        )
        logger.info(f"[FIRMS Job] Finished successfully. Upserted {count} hotspots.")
    except Exception as e:
        logger.error(f"[FIRMS Job] Failed: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()


def run_openmeteo_job():
    """Job function triggered every 1 minute to run weather ingestion & PySpark ML predictions via MeteoService."""
    logger.info("--- [JOB START] Open-Meteo & ML Prediction Service ---")
    session = SessionLocal()
    try:
        meteo_service = MeteoService(session)
        # Service handles weather ingestion, DB upsert, forecast extraction, ML predictions & prediction upsert
        result = meteo_service.run_meteo_pipeline(
            grid_precision=1.0,
            batch_size=100,
            forecast_days=7,
            past_days=0
        )
        logger.info(
            f"[Open-Meteo Job] Finished successfully. "
            f"Weather Upserted: {result.get('weather_upserted', 0)} | "
            f"Predictions Upserted: {result.get('predictions_upserted', 0)}"
        )
    except Exception as e:
        logger.error(f"[Open-Meteo Job] Failed: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()


def start_scheduler():
    """Initializes and runs the independent interval jobs."""
    scheduler = BlockingScheduler()

    # 1. FIRMS Service Job: Every 30 seconds
    scheduler.add_job(
        func=run_firms_job,
        trigger=IntervalTrigger(minutes=1),
        id="firms_30s_job",
        name="NASA FIRMS Ingestion (30s)",
        replace_existing=True,
        max_instances=1  # Prevent overlapping execution if network slows down
    )

    # 2. Open-Meteo & ML Prediction Service Job: Every 1 minute (60 seconds)
    scheduler.add_job(
        func=run_openmeteo_job,
        trigger=IntervalTrigger(minutes=5),
        id="openmeteo_1m_job",
        name="Open-Meteo & ML Pipeline (1m)",
        replace_existing=True,
        max_instances=1
    )

    logger.info("Scheduler started! FIRMS=30s | Open-Meteo & ML=1m. Press Ctrl+C to stop.")

    # Execute both jobs once immediately on startup for testing
    run_firms_job()
    run_openmeteo_job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped manually.")


if __name__ == "__main__":
    start_scheduler()