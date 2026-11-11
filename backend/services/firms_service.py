import logging
import pandas as pd
from typing import Optional
from sqlalchemy.orm import Session

from fetchers.firms_fetcher import FIRMSFetcher
from repositories.region import RegionRepository
from repositories.hotspot import HotspotRepository

logger = logging.getLogger("FIRMSService")


class FIRMSService:
    """
    Service layer orchestrating FIRMS hotspot retrieval and database upsert operations.
    """

    def __init__(self, session: Session):
        self.session = session
        self.region_repo = RegionRepository(session)
        self.hotspot_repo = HotspotRepository(session)
        self.fetcher = FIRMSFetcher(session)

    def run_ingestion(
        self,
        target_date: Optional[str] = None,
        day_range: int = 1,
        source: str = "VIIRS_SNPP_NRT",
    ) -> int:
        """
        Runs the complete FIRMS workflow:
        1. Loads all regions from the database.
        2. Fetches active fire hotspots.
        3. Upserts hotspots into PostgreSQL.
        
        Returns the total count of upserted hotspots.
        """
        # 1. Fetch regions from DB
        all_regions = self.region_repo.get_all()
        if not all_regions:
            logger.warning("[FIRMSService] No regions found in database. Aborting.")
            return 0

        logger.info(
            f"[FIRMSService] Loaded {len(all_regions)} regions. "
            f"Fetching hotspots (Date: {target_date or 'Latest'}, Day Range: {day_range})..."
        )

        # 2. Execute spatial fetcher
        hotspots = self.fetcher.fetch_hotspots(
            day_range=day_range,
            source=source,
            date=target_date,
            regions=all_regions,
        )

        # Ensure we have a valid non-empty DataFrame/list
        if hotspots is None or (isinstance(hotspots, pd.DataFrame) and hotspots.empty):
            logger.info("[FIRMSService] No hotspots retrieved for the given parameters.")
            return 0

        # Convert to DataFrame if returned as ORM objects/dicts
        if not isinstance(hotspots, pd.DataFrame):
            hotspots = pd.DataFrame(hotspots)

        # 3. Upsert into Database via HotspotRepository
        inserted_count = self.hotspot_repo.upsert_hotspots(hotspots)
        logger.info(f"[FIRMSService] Successfully upserted {inserted_count} hotspots.")

        return inserted_count