import pandas as pd
from database import SessionLocal
from fetchers.firms_fetcher import FIRMSFetcher
from repositories.region import RegionRepository
from repositories.hotspot import HotspotRepository
from datetime import datetime

session = SessionLocal()

try:
    fetcher = FIRMSFetcher(session)
    region_repo = RegionRepository(session)
    hotspot_repo = HotspotRepository(session)

    # 1. Fetch all regions from DB
    all_regions = region_repo.get_all()
    if not all_regions:
        print("[test_fetcher] No regions found in database.")
    else:
        region_ids = [r.region_id for r in all_regions]
        target_date = "2026-09-12"
        #target_date = datetime.now().strftime("%Y-%m-%d")
        day_range = 1

        print(f"[test_fetcher] Loaded {len(region_ids)} regions. Running query for target date {target_date}...")

        # 2. Execute fetcher (Uses fast cKDTree spatial search & bulk DB insert)
        hotspots = fetcher.fetch_hotspots(
            day_range=day_range,
            source="VIIRS_SNPP_NRT",
            date=target_date,
            regions = all_regions
        )

        print(f"\n--- Result: {len(hotspots)} hotspots found ---")
        if isinstance(hotspots, pd.DataFrame):
            print(hotspots.head(20))
        else:
            print(pd.DataFrame(hotspots).head())

        # 3. Test saving
        if hotspots is not None and not hotspots.empty:
        
            inserted_count = hotspot_repo.upsert_hotspots(hotspots)
            print(f"[test_fetcher] Upserted {inserted_count} hotspots into the database.")

finally:
    session.close()