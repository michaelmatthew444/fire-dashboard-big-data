import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from yarl import Query

from services.hotspot_map_service import HotspotMapService
from services.data_service import DataService

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from database import SessionLocal
# Connect directly to your existing scheduler functions
from scheduler import run_firms_job, run_openmeteo_job

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MainApplication")

# Initialize BackgroundScheduler (runs non-blocking in background threads)
background_scheduler = BackgroundScheduler()


# --- FastAPI Lifespan Handler ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    Wires your existing scheduler.py functions directly into the FastAPI lifecycle.
    """
    logger.info("Initializing background scheduler jobs from scheduler.py...")
    
    # 1. Attach FIRMS Ingestion Job (Every 30 seconds)
    background_scheduler.add_job(
        func=run_firms_job,
        trigger=IntervalTrigger(seconds=30),
        id="firms_30s_job",
        name="NASA FIRMS Hotspots Ingestion (30s)",
        replace_existing=True,
        max_instances=1
    )
    
    # 2. Attach Open-Meteo & PySpark ML Job (Every 1 minute)
    background_scheduler.add_job(
        func=run_openmeteo_job,
        trigger=IntervalTrigger(minutes=1),
        id="openmeteo_1m_job",
        name="Open-Meteo Weather & PySpark ML Pipeline (1m)",
        replace_existing=True,
        max_instances=1
    )
    
    # 3. Start Background Scheduler
    background_scheduler.start()
    logger.info("Background scheduler successfully started! (FIRMS: 30s | Meteo+ML: 1m)")

    yield  # FastAPI serves HTTP requests here

    # 4. Graceful Shutdown
    logger.info("Shutting down background scheduler...")
    background_scheduler.shutdown(wait=False)


# --- FastAPI Application Setup ---

app = FastAPI(
    title="Fire Risk Detection & Ingestion Engine",
    version="1.0.0",
    description="Backend service orchestrating NASA FIRMS, Open-Meteo API, PySpark ML, and PostgreSQL storage.",
    lifespan=lifespan
)

# Enable CORS for frontend dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to supply DB sessions for API routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- API Endpoints ---

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Fire Risk Prediction Engine & API Operational",
        "scheduler": "running"
    }

@app.get("/api/hotspots/map")
def get_hotspots_map(
    mode: str = "historical",
    db: Session = Depends(get_db)
):
    """
    Retrieves hotspot or forecast prediction data for map visualization.
    """
    if mode not in ["historical", "forecast"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid mode. Allowed values are 'historical' or 'forecast'."
        )

    try:
        service = HotspotMapService(db)
        result = service.get_map_data(mode)
        return result

    except Exception as e:
        logger.error(f"Failed to retrieve map data for mode '{mode}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving map data for mode '{mode}'.")

@app.get("/api/data")
def get_data(region_id: int = 1, db: Session = Depends(get_db)):
    """
    Retrieve all necessary data for dashboard
    """

    try:
        data_service = DataService(db)
        result = data_service.get_data(region_id=region_id)
        return result
    except Exception as e:
        logger.error(f"Error serving data dashboard endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving weather table data.")

    return {"region_id": region_id, "data": []}

@app.get("/api/data/table/meteorology")
def get_weather_table(
    region_id: int = 1,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """
    Retrieves the meteorological history table ordered by region, acquisition date, and time, 
    with pagination (10 items per page by default).
    """
    try:
        data_service = DataService(db)
        result = data_service.get_meteorological_table_paginated(
            region_id=region_id, page=page, page_size=page_size
        )
        return result
    except Exception as e:
        logger.error(f"Error serving weather table endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving weather table data.")


@app.get("/api/data/table/hotspot")
def get_weather_table(
    region_id: int = 1,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """
    Retrieves the meteorological hotspot table ordered by region, acquisition date, and time, 
    with pagination (10 items per page by default).
    """
    try:
        data_service = DataService(db)
        result = data_service.get_hotspot_table_paginated(
            region_id=region_id, page=page, page_size=page_size
        )
        return result
    except Exception as e:
        logger.error(f"Error serving hotspot table endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving hotspot table data.")


@app.get("/api/data/region")
def get_all_region_ids(db: Session = Depends(get_db)):
    try:
        data_service = DataService(db)
        result = data_service.get_all_region_ids()
        return result
    except Exception as e:
        logger.error(f"Error serving all region ids endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving region ids data.")

        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)