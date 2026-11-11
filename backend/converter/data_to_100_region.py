import os
import json
import numpy as np
from typing import List, Dict, Any
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely import make_valid


class KalimantanRegionClustererJSON:
    """
    Clusters micro-polygons from a raw GeoJSON dictionary/JSON file into macro-regions
    without requiring GeoPandas, handling invalid geometries safely.
    """

    def __init__(
        self,
        input_json_path: str = "data/kalimantan_regions.geojson",
        output_json_path: str = "data/kalimantan_100_regions.geojson",
        target_clusters: int = 100
    ):
        self.input_json_path = input_json_path
        self.output_json_path = output_json_path
        self.target_clusters = target_clusters

    def process_and_cluster(self) -> Dict[str, Any]:
        if not os.path.exists(self.input_json_path):
            raise FileNotFoundError(f"Input file not found: {self.input_json_path}")

        print(f"[RegionClustererJSON] Loading JSON from '{self.input_json_path}'...")
        with open(self.input_json_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

        features = geojson_data.get("features", [])
        original_count = len(features)
        print(f"[RegionClustererJSON] Found {original_count} original micro-features.")

        if original_count == 0:
            print("[RegionClustererJSON] Feature list is empty.")
            return {"type": "FeatureCollection", "features": []}

        valid_records = []
        centroids = []

        # 1. Parse shapes & repair invalid geometries with make_valid / buffer(0)
        for feat in features:
            geom = feat.get("geometry")
            if not geom or not isinstance(geom, dict):
                continue

            try:
                poly_shape = shape(geom)
                if poly_shape.is_empty:
                    continue

                # Repair invalid geometry topology
                if not poly_shape.is_valid:
                    poly_shape = make_valid(poly_shape)
                    if poly_shape.is_empty:
                        continue

                c = poly_shape.centroid
                centroids.append([c.x, c.y])
                valid_records.append({
                    "feature": feat,
                    "shape": poly_shape
                })
            except Exception:
                continue

        if not valid_records:
            print("[RegionClustererJSON] No valid polygon geometries could be parsed.")
            return {"type": "FeatureCollection", "features": []}

        coords = np.array(centroids)

        # 2. Bin centroids into spatial quantiles
        grid_dim = int(np.ceil(np.sqrt(min(self.target_clusters, len(valid_records)))))
        
        x_bins = np.unique(np.quantile(coords[:, 0], np.linspace(0, 1, grid_dim + 1)))
        y_bins = np.unique(np.quantile(coords[:, 1], np.linspace(0, 1, grid_dim + 1)))

        clusters: Dict[str, List[Any]] = {}

        for record, (x, y) in zip(valid_records, coords):
            x_idx = np.digitize(x, x_bins) - 1
            y_idx = np.digitize(y, y_bins) - 1
            cluster_key = f"{x_idx}_{y_idx}"
            
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(record["shape"])

        print(f"[RegionClustererJSON] Formed {len(clusters)} macro clusters. Merging geometries...")

        # 3. Safely dissolve internal borders per cluster
        macro_features = []
        region_id_counter = 1

        for cluster_key, shapes_list in clusters.items():
            try:
                # Primary dissolve attempt
                merged_shape = unary_union(shapes_list)
            except Exception:
                # Fallback: repair shapes using buffer(0) then retry unary_union
                repaired_shapes = [s.buffer(0) if not s.is_valid else s for s in shapes_list]
                merged_shape = unary_union(repaired_shapes)

            if merged_shape.is_empty:
                continue

            # Ensure final output geometry topology is valid
            if not merged_shape.is_valid:
                merged_shape = make_valid(merged_shape)

            macro_centroid = merged_shape.centroid

            macro_feature = {
                "type": "Feature",
                "geometry": mapping(merged_shape),
                "properties": {
                    "region_id": region_id_counter,
                    "cluster_id": cluster_key,
                    "centroid_latitude": round(macro_centroid.y, 6),
                    "centroid_longitude": round(macro_centroid.x, 6)
                }
            }
            macro_features.append(macro_feature)
            region_id_counter += 1

        output_geojson = {
            "type": "FeatureCollection",
            "features": macro_features
        }

        # 4. Save clean GeoJSON
        print(f"[RegionClustererJSON] Saving {len(macro_features)} macro-regions to '{self.output_json_path}'...")
        os.makedirs(os.path.dirname(self.output_json_path) or ".", exist_ok=True)
        with open(self.output_json_path, "w", encoding="utf-8") as f:
            json.dump(output_geojson, f, indent=2)

        print("\n" + "=" * 50)
        print(" JSON CLUSTERING SUCCESSFUL")
        print("=" * 50)
        print(f"Original Micro-Regions : {original_count}")
        print(f"Macro-Regions Created  : {len(macro_features)}")

        return output_geojson


if __name__ == "__main__":
    clusterer = KalimantanRegionClustererJSON(
        input_json_path="data/kalimantan_regions.geojson",
        output_json_path="data/kalimantan_100_regions.geojson",
        target_clusters=100
    )
    result = clusterer.process_and_cluster()