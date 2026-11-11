import io
import requests
import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Any
from scipy.spatial import cKDTree
from sqlalchemy.orm import Session

from config import NASA_FIRMS_MAP_KEY, CURR_BBOX
from repositories.region import RegionRepository


class FIRMSFetcher:


    def __init__(self, session: Session, map_key: str = NASA_FIRMS_MAP_KEY):
        self.session = session
        self.map_key = map_key

    def fetch_hotspots(
        self,
        day_range: int = 1,
        source: str = "VIIRS_SNPP_NRT",
        date: Optional[str] = None,
        max_dist_deg: Optional[float] = 0.05,
        regions: Optional[List[Any]] = None,
    ) -> pd.DataFrame:

        # 1. Check if regions valid

        if not regions:
            print("[FIRMSFetcherIndonesia] No valid regions found with centroids.")
            return pd.DataFrame()


        # 2. Request FIRMS API using the single Indonesia Bounding Box
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{self.map_key}/{source}/{CURR_BBOX}/{day_range}"
        if date:
            url += f"/{date}"

        print(f"[FIRMSFetcherIndonesia] Requesting FIRMS API for Indonesia BBox on Date: {date or 'Latest'}...")
        response = requests.get(url)

        if response.status_code != 200 or not response.text.strip():
            print(f"[FIRMSFetcherIndonesia] No data returned or API error {response.status_code}.")
            return pd.DataFrame()

        df_hotspots = pd.read_csv(io.StringIO(response.text))
        if df_hotspots.empty:
            print("[FIRMSFetcherIndonesia] API returned empty dataset.")
            return pd.DataFrame()

        # Ensure correct column fallback standard headers
        df_hotspots["bright_ti4"] = df_hotspots.get("bright_ti4", df_hotspots.get("brightness", 0.0)).astype(float)
        df_hotspots["bright_ti5"] = df_hotspots.get("bright_ti5", df_hotspots.get("bright_t31", 0.0)).astype(float)
        df_hotspots["frp"] = df_hotspots.get("frp", 0.0).astype(float)

        # 3. Fast Spatial Matching using cKDTree over all ~64k regions
        region_coords = np.array([[r.centroid_latitude, r.centroid_longitude] for r in regions])
        tree = cKDTree(region_coords)

        distances, indices = tree.query(df_hotspots[["latitude", "longitude"]].to_numpy(), workers=-1)

        df_hotspots["region_id"] = [regions[idx].region_id for idx in indices]
        df_hotspots["dist_deg"] = distances

        # Optional threshold filtering (e.g., discard hotspots farther than max_dist_deg from any centroid)
        if max_dist_deg is not None:
            df_hotspots = df_hotspots[df_hotspots["dist_deg"] <= max_dist_deg]

        if df_hotspots.empty:
            print("[FIRMSFetcherIndonesia] No hotspots remained after distance filtering.")
            return pd.DataFrame()

        # 4. Deduplicate per region_id: Keep the row with the MAX brightness temperature
        df_sorted = df_hotspots.sort_values(by="bright_ti4", ascending=False)
        df_deduped = df_sorted.drop_duplicates(subset=["region_id"], keep="first").copy()

        print(f"[FIRMSFetcherIndonesia] Matched {len(df_deduped)} unique hotspot-region pairs successfully.")
        
        # Returns clean DataFrame without saving to database
        return df_deduped[["region_id", "latitude", "longitude", "bright_ti4", "bright_ti5", "frp", "acq_date", "acq_time", "daynight", "dist_deg"]]