# services/data_service.py
from datetime import date
import logging
import math
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from repositories.weather import WeatherRepository
from repositories.hotspot import HotspotRepository
from repositories.region import RegionRepository

logger = logging.getLogger("DataService")


class DataService:
    """
    Service layer handling dashboard metric retrieval and formatting.
    """

    def __init__(self, db: Session):
        self.db = db
        self.weather_repo = WeatherRepository(db)
        self.hotspot_repo = HotspotRepository(db)
        self.region_repo = RegionRepository(db)

    def get_all_region_ids(self) -> Dict[str, Any]:
        try:
            region_ids = self.region_repo.get_all_region_ids()
            return {
                "data": region_ids
            }
        except Exception as e:
            logger.error(f"Failed to retrieve all region ids: {e}", exc_info=True)
            raise e

    def get_data(self, region_id: Optional[int] = None) -> Dict[str, Any]:
        """
        1. Obtain Meteorlogical_cards
        2. Obtain Line Graph
        3. Obtain Meteorlogy Table
        4. Obtain Hotspot Table
        """

        try:
            record_cards = self.get_meteorological_cards(region_id=region_id)
            record_line = self.get_today_line_graph(region_id=region_id)
            record_meteorology_table = self.get_meteorological_table_paginated(region_id=region_id, page=1, page_size=10)
            record_hotspot_table = self.get_hotspot_table_paginated(region_id=region_id, page=1, page_size=10)


            return {
                "region_id": region_id,
                "record_cards": record_cards,
                "record_line": record_line,
                "record_meteorology_table": record_meteorology_table,
                "record_hotspot_table": record_hotspot_table
            }
        except Exception as e:
            logger.error(f"Failed to retrieve data info: {e}", exc_info=True)
            raise e


    def get_meteorological_cards(self, region_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieves and formats statistics for the 10 meteorological dashboard cards.
        Supports filtering by region_id or returning domain-wide statistics.
        """
        try:
            stats = self.weather_repo.get_weather_card_stats(region_id=region_id)

            if not stats or stats.get("latest_date") is None:
                logger.info(f"No weather data available for region_id={region_id}")
                return {"cards": [], "latest_timestamp": None, "region_id": region_id}

            cards: List[Dict[str, Any]] = [
                {
                    "key": "temperature_2m",
                    "label": "Air Temperature (2m)",
                    "unit": "°C",
                    "current": stats.get("current_temp"),
                    "min": stats.get("min_temp"),
                    "avg": stats.get("avg_temp"),
                    "max": stats.get("max_temp"),
                },
                {
                    "key": "humidity_2m",
                    "label": "Relative Humidity (2m)",
                    "unit": "%",
                    "current": stats.get("current_hum"),
                    "min": stats.get("min_hum"),
                    "avg": stats.get("avg_hum"),
                    "max": stats.get("max_hum"),
                },
                {
                    "key": "precipitation",
                    "label": "Precipitation",
                    "unit": "mm",
                    "current": stats.get("current_precip"),
                    "min": stats.get("min_precip"),
                    "avg": stats.get("avg_precip"),
                    "max": stats.get("max_precip"),
                },
                {
                    "key": "wind_speed_10m",
                    "label": "Wind Speed (10m)",
                    "unit": "km/h",
                    "current": stats.get("current_wind"),
                    "min": stats.get("min_wind"),
                    "avg": stats.get("avg_wind"),
                    "max": stats.get("max_wind"),
                },
                {
                    "key": "surface_pressure",
                    "label": "Surface Pressure",
                    "unit": "hPa",
                    "current": stats.get("current_press"),
                    "min": stats.get("min_press"),
                    "avg": stats.get("avg_press"),
                    "max": stats.get("max_press"),
                },
                {
                    "key": "cloud_cover",
                    "label": "Cloud Cover",
                    "unit": "%",
                    "current": stats.get("current_cloud"),
                    "min": stats.get("min_cloud"),
                    "avg": stats.get("avg_cloud"),
                    "max": stats.get("max_cloud"),
                },
                {
                    "key": "soil_temp_0_7",
                    "label": "Soil Temp (0-7cm)",
                    "unit": "°C",
                    "current": stats.get("current_soil_temp_top"),
                    "min": stats.get("min_soil_temp_top"),
                    "avg": stats.get("avg_soil_temp_top"),
                    "max": stats.get("max_soil_temp_top"),
                },
                {
                    "key": "soil_temp_7_28",
                    "label": "Soil Temp (7-28cm)",
                    "unit": "°C",
                    "current": stats.get("current_soil_temp_deep"),
                    "min": stats.get("min_soil_temp_deep"),
                    "avg": stats.get("avg_soil_temp_deep"),
                    "max": stats.get("max_soil_temp_deep"),
                },
                {
                    "key": "soil_moisture_0_7",
                    "label": "Soil Moisture (0-7cm)",
                    "unit": "m³/m³",
                    "current": stats.get("current_soil_moist_top"),
                    "min": stats.get("min_soil_moist_top"),
                    "avg": stats.get("avg_soil_moist_top"),
                    "max": stats.get("max_soil_moist_top"),
                },
                {
                    "key": "soil_moisture_7_28",
                    "label": "Soil Moisture (7-28cm)",
                    "unit": "m³/m³",
                    "current": stats.get("current_soil_moist_deep"),
                    "min": stats.get("min_soil_moist_deep"),
                    "avg": stats.get("avg_soil_moist_deep"),
                    "max": stats.get("max_soil_moist_deep"),
                },
            ]

            latest_ts = f"{stats.get('latest_date')} {stats.get('latest_time')}"

            return {
                "region_id": region_id,
                "latest_timestamp": latest_ts,
                "cards": cards,
            }

        except Exception as e:
            logger.error(f"Failed to retrieve weather card stats: {e}", exc_info=True)
            raise e

    def get_today_line_graph(
        self, region_id: int = 1, target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Retrieves 24 hourly weather observations/forecasts for the line graph.
        Defaults to today's date if target_date is not specified.
        """
        try:
            # Default to today's date if no date provided
            query_date = target_date or date.today()

            logger.info(
                f"Fetching 24-hour line graph data for region_id={region_id}, date={query_date}"
            )
            hourly_records = self.weather_repo.get_hourly_weather_by_date(
                region_id=region_id, target_date=query_date
            )

            return {
                "region_id": region_id,
                "target_date": str(query_date),
                "total_hours": len(hourly_records),
                "hourly_data": hourly_records,
            }

        except Exception as e:
            logger.error(
                f"Failed to retrieve line graph data for region_id={region_id}: {e}",
                exc_info=True,
            )
            raise e

    def get_meteorological_table_paginated(
        self, region_id: Optional[int] = None, page: int = 1, page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieves paginated meteorological table data grouped by region, 
        ordered by acquisition date and time.
        """
        try:
            records = self.weather_repo.get_paginated_weather_table(
                region_id=region_id, page=page, page_size=page_size
            )

            total_items = self.weather_repo.count_weather_records(region_id=region_id)
            
            # Compute max pages (at least 1 page even if empty)
            max_page = math.ceil(total_items / page_size) if total_items > 0 else 1

            formatted_records = [
                {
                    "weather_id": w.weather_id,
                    "region_id": w.region_id,
                    "temperature_2m": w.temperature_2m,
                    "humidity_2m": w.humidity_2m,
                    "precipitation": w.precipitation,
                    "wind_speed_10m": w.wind_speed_10m,
                    "surface_pressure": w.surface_pressure,
                    "cloud_cover": w.cloud_cover,
                    "acq_date": str(w.acq_date) if w.acq_date else None,
                    "acq_time": w.acq_time,
                    "target_date": str(w.target_date) if w.target_date else None,
                    "target_time": w.target_time,
                    "is_forecast": w.is_forecast,
                }
                for w in records
            ]

            return {
                "region_id": region_id,
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "max_page": max_page,
                "data": formatted_records,
            }

        except Exception as e:
            logger.error(f"Failed to retrieve paginated weather table: {e}", exc_info=True)
            raise e


    def get_hotspot_table_paginated(
        self, region_id: Optional[int] = None, page: int = 1, page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieves paginated hotspot table data grouped by region,
        ordered by acquisition date and time.
        """
        try:
            records = self.hotspot_repo.get_paginated_hotspot_table(
                region_id=region_id, page=page, page_size=page_size
            )

            total_items = self.hotspot_repo.count_hotspot_records(region_id=region_id)
            
            # Compute max pages (at least 1 page even if empty)
            max_page = math.ceil(total_items / page_size) if total_items > 0 else 1

            formatted_records = [
                {
                    "hotspot_id": h.hotspot_id,
                    "region_id": h.region_id,
                    "bright_ti4": h.bright_ti4,
                    "acq_date": str(h.acq_date) if h.acq_date else None,
                    "acq_time": h.acq_time,
                    "bright_ti5": h.bright_ti5,
                    "frp": h.frp,
                    "daynight": h.daynight,
                }
                for h in records
            ]

            return {
                "region_id": region_id,
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "max_page": max_page,
                "data": formatted_records,
            }

        except Exception as e:
            logger.error(f"Failed to retrieve paginated hotspot table: {e}", exc_info=True)
            raise e