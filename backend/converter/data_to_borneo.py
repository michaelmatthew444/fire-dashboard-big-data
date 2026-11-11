import json

INPUT_GEOJSON_PATH = "data/map.json"
OUTPUT_GEOJSON_PATH = "data/kalimantan_regions.geojson"

MIN_LON, MAX_LON = 108.5, 119.0
MIN_LAT, MAX_LAT = -4.5, 4.5

def get_feature_centroid(geometry):
    """Extracts a representative (lon, lat) coordinate for spatial checking."""
    # Safety check if geometry is None or empty
    if not geometry or not isinstance(geometry, dict):
        return None, None

    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])

    if not coords:
        return None, None

    if geom_type == "Point":
        return coords[0], coords[1]
    
    elif geom_type in ["Polygon", "MultiPolygon"]:
        all_lons = []
        all_lats = []
        
        def extract_pts(c_list):
            for elem in c_list:
                if isinstance(elem, (list, tuple)) and len(elem) >= 2 and isinstance(elem[0], (float, int)):
                    all_lons.append(elem[0])
                    all_lats.append(elem[1])
                elif isinstance(elem, list):
                    extract_pts(elem)

        extract_pts(coords)
        if all_lons and all_lats:
            return sum(all_lons) / len(all_lons), sum(all_lats) / len(all_lats)

    return None, None

def filter_kalimantan_geojson(input_path: str, output_path: str):
    print(f"Loading GeoJSON from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    original_features = geojson_data.get("features", [])
    kalimantan_features = []
    skipped_count = 0

    for feature in original_features:
        if not feature or not isinstance(feature, dict):
            skipped_count += 1
            continue

        geometry = feature.get("geometry")
        lon, lat = get_feature_centroid(geometry)

        if lon is not None and lat is not None:
            if MIN_LON <= lon <= MAX_LON and MIN_LAT <= lat <= MAX_LAT:
                kalimantan_features.append(feature)
        else:
            skipped_count += 1

    filtered_geojson = {
        "type": "FeatureCollection",
        "features": kalimantan_features
    }

    print(f"Writing filtered GeoJSON to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(filtered_geojson, f, indent=2)

    print("\n" + "=" * 50)
    print(" FILTER SUMMARY")
    print("=" * 50)
    print(f"Original Feature Count   : {len(original_features)}")
    print(f"Kalimantan Feature Count : {len(kalimantan_features)}")
    print(f"Skipped / Invalid Geoms  : {skipped_count}")

if __name__ == "__main__":
    filter_kalimantan_geojson(INPUT_GEOJSON_PATH, OUTPUT_GEOJSON_PATH)