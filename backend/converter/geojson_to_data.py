import os
import json
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text, create_engine

# Database Connection URI
DB_URI = "postgresql://matthew:fire1234@localhost:5432/fire_forest_db"

# JSON File Path
JSON_PATH = r"data\kalimantan_100_regions.geojson"


def load_region_json(file_path: str) -> pd.DataFrame:
    """Reads the clustered 100-region JSON file and extracts region properties."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at path: {file_path}")

    print(f"Loading region JSON from '{file_path}'...")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    records = []

    for idx, feature in enumerate(features, start=1):
        props = feature.get("properties", {})
        
        # Extract region_id, latitude, and longitude from feature properties
        region_id = props.get("region_id", idx)
        lat = props.get("centroid_latitude")
        lon = props.get("centroid_longitude")

        records.append({
            "region_id": int(region_id),
            "centroid_longitude": float(lon) if lon is not None else None,
            "centroid_latitude": float(lat) if lat is not None else None,
        })

    region_df = pd.DataFrame(records)
    print(f"Parsed {len(region_df)} macro-regions successfully.")
    return region_df


def upload_to_postgres(region_df: pd.DataFrame):
    print("Connecting to PostgreSQL...")
    engine = create_engine(DB_URI)

    with engine.begin() as conn:
        print("Truncating old region records and dependent child records...")
        # TRUNCATE CASCADE safely clears region and linked hotspot/weather data without dropping the schema
        conn.execute(text("TRUNCATE TABLE region CASCADE;"))

    print(f"Ingesting {len(region_df)} records into 'region' table...")
    region_df.to_sql(
        name="region",
        con=engine,
        if_exists="append",  # Use append since TRUNCATE cleared the table safely
        index=False,
        method="multi",
        chunksize=5000,
    )
    print("Successfully populated the 'region' table!")


if __name__ == "__main__":
    # 1. Load and parse the 100 regions JSON file
    region_df = load_region_json(JSON_PATH)

    print("\nSample Data to be Ingested:")
    print(region_df.head())

    # 2. Ingest data into PostgreSQL
    upload_to_postgres(region_df)