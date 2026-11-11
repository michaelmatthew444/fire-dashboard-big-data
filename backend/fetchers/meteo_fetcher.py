import time
import requests
import pandas as pd
from typing import Optional, List, Any
from sqlalchemy.orm import Session


class OpenMeteoFetcher:

    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, session: Session):
        self.session = session

    def fetch_weather_for_regions(
        self,
        grid_precision: float = 0.2,
        batch_size: int = 100,
        mode: str = "forecast",        # Default mode: "forecast" (options: "forecast", "historical")
        forecast_days: int = 3,         # Used in forecast mode (default: 3)
        past_days: int = 0,             # Used in forecast mode for recent past relative window
        start_date: Optional[str] = None, # Explicit "YYYY-MM-DD" for historical/custom date query
        end_date: Optional[str] = None,   # Explicit "YYYY-MM-DD" for historical/custom date query
        extract_current_hour_only: bool = False,
        regions: Optional[List[Any]] = None
    ) -> pd.DataFrame:
        """
        Fetches hourly weather data for regions.
        - mode="forecast": Uses Forecast API for current and upcoming forecast days.
        - mode="historical": Uses Archive API for specific past date ranges.
        """
        if not regions:
            print("[OpenMeteoFetcher] No valid regions found.")
            return pd.DataFrame()

        # 1. Round coordinates to spatial grid
        df_regions = pd.DataFrame([
            {
                "region_id": r.region_id,
                "lat": r.centroid_latitude,
                "lon": r.centroid_longitude,
                "grid_lat": round(round(r.centroid_latitude / grid_precision) * grid_precision, 2),
                "grid_lon": round(round(r.centroid_longitude / grid_precision) * grid_precision, 2),
            }
            for r in regions
        ])

        unique_grids = df_regions[["grid_lat", "grid_lon"]].drop_duplicates().reset_index(drop=True)
        print(
            f"[OpenMeteoFetcher] Clustered {len(df_regions)} regions into {len(unique_grids)} grid points "
            f"(Mode: '{mode}')."
        )

        weather_records = []

        # Comprehensive list of parameters requested from Open-Meteo
        requested_hourly_params = [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "precipitation",
            "surface_pressure",
            "soil_temperature_0_to_7cm",
            "soil_temperature_7_to_28cm",
            "soil_moisture_0_to_7cm",
            "soil_moisture_7_to_28cm",
            "cloud_cover"
        ]

        # Current time in Jakarta timezone for forecast flag evaluation
        now_ts = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)

        # Determine target API endpoint
        url = self.HISTORICAL_URL if mode == "historical" else self.FORECAST_URL

        # 2. Query Open-Meteo in paced batches
        for i in range(0, len(unique_grids), batch_size):
            batch = unique_grids.iloc[i : i + batch_size]
            lats_str = ",".join(batch["grid_lat"].astype(str))
            lons_str = ",".join(batch["grid_lon"].astype(str))

            params = {
                "latitude": lats_str,
                "longitude": lons_str,
                "hourly": ",".join(requested_hourly_params),
                "timezone": "Asia/Jakarta"
            }

            # Configure date range / duration parameters based on mode and explicitly passed dates
            if start_date and end_date:
                params["start_date"] = start_date
                params["end_date"] = end_date
            elif mode == "historical":
                # Default historical past window if no explicit start/end dates provided
                days_back = past_days if past_days > 0 else 7
                params["start_date"] = (now_ts - pd.Timedelta(days=days_back)).strftime("%Y-%m-%d")
                params["end_date"] = now_ts.strftime("%Y-%m-%d")
            else:  # mode == "forecast"
                params["forecast_days"] = max(1, forecast_days)
                if past_days > 0:
                    params["past_days"] = past_days

            max_retries = 3
            for attempt in range(max_retries):
                response = requests.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    results = data if isinstance(data, list) else [data]

                    for grid_row, res in zip(batch.itertuples(), results):
                        hourly = res.get("hourly", {})
                        times = hourly.get("time", [])
                        temps = hourly.get("temperature_2m", [])
                        hums = hourly.get("relative_humidity_2m", [])
                        winds = hourly.get("wind_speed_10m", [])
                        precips = hourly.get("precipitation", [])
                        pressures = hourly.get("surface_pressure", [])
                        soil_temp_0 = hourly.get("soil_temperature_0_to_7cm", [])
                        soil_temp_7 = hourly.get("soil_temperature_7_to_28cm", [])
                        soil_moist_0 = hourly.get("soil_moisture_0_to_7cm", [])
                        soil_moist_7 = hourly.get("soil_moisture_7_to_28cm", [])
                        clouds = hourly.get("cloud_cover", [])

                        indices_to_extract = [0] if extract_current_hour_only else range(len(times))

                        for idx in indices_to_extract:
                            if idx < len(times):
                                raw_time = times[idx]
                                record_dt = pd.to_datetime(raw_time)

                                # Mark as forecast if timestamp is in the future
                                is_forecast_val = record_dt > now_ts if mode == "forecast" else False

                                weather_records.append({
                                    "grid_lat": grid_row.grid_lat,
                                    "grid_lon": grid_row.grid_lon,
                                    "raw_acq_time": raw_time,
                                    "temperature_2m": temps[idx] if idx < len(temps) else None,
                                    "humidity_2m": hums[idx] if idx < len(hums) else None,
                                    "precipitation": precips[idx] if idx < len(precips) else None,
                                    "wind_speed_10m": winds[idx] if idx < len(winds) else None,
                                    "surface_pressure": pressures[idx] if idx < len(pressures) else None,
                                    "soil_temperature_0_to_7cm": soil_temp_0[idx] if idx < len(soil_temp_0) else None,
                                    "soil_temperature_7_to_28cm": soil_temp_7[idx] if idx < len(soil_temp_7) else None,
                                    "soil_moisture_0_to_7cm": soil_moist_0[idx] if idx < len(soil_moist_0) else None,
                                    "soil_moisture_7_to_28cm": soil_moist_7[idx] if idx < len(soil_moist_7) else None,
                                    "cloud_cover": clouds[idx] if idx < len(clouds) else None,
                                    "is_forecast": is_forecast_val
                                })
                    break

                elif response.status_code == 429:
                    wait_time = (attempt + 1) * 5
                    print(f"[OpenMeteoFetcher] 429 Rate Limit. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"[OpenMeteoFetcher] Error {response.status_code} on batch {i}")
                    break

            time.sleep(0.2)

        if not weather_records:
            return pd.DataFrame()

        df_weather = pd.DataFrame(weather_records)

        # 3. Map back to regions
        df_merged = pd.merge(df_regions, df_weather, on=["grid_lat", "grid_lon"], how="inner")

        acq_dt = pd.to_datetime(df_merged["raw_acq_time"])
        df_merged["acq_date"] = acq_dt.dt.date
        df_merged["acq_time"] = acq_dt.dt.strftime("%H:%M")
        df_merged["target_date"] = acq_dt.dt.date
        df_merged["target_time"] = acq_dt.dt.strftime("%H:%M")

        cols = [
            "region_id",
            "temperature_2m",
            "humidity_2m",
            "precipitation",
            "wind_speed_10m",
            "surface_pressure",
            "soil_temperature_0_to_7cm",
            "soil_temperature_7_to_28cm",
            "soil_moisture_0_to_7cm",
            "soil_moisture_7_to_28cm",
            "cloud_cover",
            "acq_date",
            "acq_time",
            "target_date",
            "target_time",
            "is_forecast"
        ]

        return df_merged[cols]