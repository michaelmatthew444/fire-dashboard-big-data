import geopandas as gpd
import os
from sqlalchemy import create_engine

os.environ["SHAPE_RESTORE_SHX"] = "YES"
region_path = "backend\data\kawasan_hutan\kawasan_hutan_092017.shp"
DB_URI = (
    "postgresql://matthew:fire1234@localhost:5432/fire_forest_db"
)


def load_region(region_path):
    gdf = gpd.read_file(region_path)
    return gdf


def extract_geometry(gdf):
    # Reproject temporarily to EPSG:3857 (meters) for accurate geometric calculations
    gdf_projected = gdf.to_crs(epsg=3857)

    # Use representative_point() instead of centroid to GUARANTEE point is inside the polygon
    points_wgs84 = gdf_projected.geometry.representative_point().to_crs(
        epsg=4326
    )

    gdf["centroid_longitude"] = points_wgs84.x
    gdf["centroid_latitude"] = points_wgs84.y

    region_df = gdf[
        ["objectid", "centroid_longitude", "centroid_latitude"]
    ].copy()
    region_df.rename(columns={"objectid": "region_id"}, inplace=True)

    return region_df

def validate_centroids(gdf):
    """Verifies that representative points fall strictly inside all 66,768 polygons."""
    gdf_projected = gdf.to_crs(epsg=3857)

    # Calculate representative points
    rep_points = gdf_projected.geometry.representative_point()

    # Point-in-polygon containment test
    is_inside = rep_points.within(gdf_projected.geometry)

    inside_count = is_inside.sum()
    outside_count = len(gdf) - inside_count

    print(f"\n--- Full Dataset Point-in-Polygon Validation ---")
    print(f"Points strictly INSIDE polygon boundary: {inside_count} / {len(gdf)}")
    print(f"Points OUTSIDE boundary: {outside_count}")

    return is_inside.all()

def upload_to_postgres(region_df):
    print(f"Connecting to PostgreSQL...")
    engine = create_engine(DB_URI)

    print(f"Ingesting {len(region_df)} records into 'region' table...")
    region_df.to_sql(
        name="region",
        con=engine,
        if_exists="append",  # Appends to your created PostgreSQL schema
        index=False,
        method="multi",
        chunksize=5000,
    )
    print("Successfully populated the 'region' table!")


if __name__ == "__main__":
    gdf = load_region(region_path)
    region_df = extract_geometry(gdf)

    #print(region_df.head())
    #is_valid = validate_centroids(gdf)

    # Ingest data into your Docker database
    upload_to_postgres(region_df)



