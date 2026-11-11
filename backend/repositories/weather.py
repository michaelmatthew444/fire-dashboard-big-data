from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, date, time
from models.weather import Weather
import pandas as pd

class WeatherRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, weather_id: int) -> Weather | None:
        return self.session.get(Weather, weather_id)

    def get_all(self) -> list[Weather]:
        return list(self.session.scalars(select(Weather)).all())

    def create(self, region_id: int, weather_data: dict) -> Weather:
        weather = Weather(region_id=region_id, **weather_data)
        self.session.add(weather)
        self.session.commit()
        self.session.refresh(weather)
        return weather

    def upsert_weather(self, df_weather: pd.DataFrame) -> int:
        """
        Bulk upserts weather records on (region_id, target_date, target_time).
        Automatically converts is_forecast to False if (target_date + target_time) <= datetime.now().
        """
        if df_weather is None or df_weather.empty:
            print("[WeatherRepository] No weather records to ingest.")
            return 0

        now = datetime.now()
        values_to_upsert = []

        for _, row in df_weather.iterrows():
            # Parse target_date
            t_date = row["target_date"]
            if isinstance(t_date, str):
                t_date = datetime.strptime(t_date, "%Y-%m-%d").date()

            # Parse target_time
            t_time_str = str(row["target_time"])
            if ":" in t_time_str:
                t_hour, t_min = map(int, t_time_str.split(":")[:2])
            else:
                t_hour, t_min = int(t_time_str[:2]), int(t_time_str[2:]) if len(t_time_str) >= 4 else 0
            
            # Create full target datetime object for comparison
            target_dt = datetime.combine(t_date, time(t_hour, t_min))

           # Inside WeatherRepository.upsert_weather loop:
            is_forecast_val = bool(row.get("is_forecast", False))

            # Only override if is_forecast was not explicitly specified or passed
            if "is_forecast" not in row or row["is_forecast"] is None:
                if target_dt <= now:
                    is_forecast_val = False

            # Parse acq_date
            a_date = row.get("acq_date")
            if isinstance(a_date, str):
                a_date = datetime.strptime(a_date, "%Y-%m-%d").date()

            values_to_upsert.append({
                "region_id": int(row["region_id"]),
                "temperature_2m": float(row["temperature_2m"]) if pd.notnull(row["temperature_2m"]) else None,
                "humidity_2m": float(row["humidity_2m"]) if pd.notnull(row["humidity_2m"]) else None,
                "precipitation": float(row["precipitation"]) if pd.notnull(row["precipitation"]) else None,
                "wind_speed_10m": float(row["wind_speed_10m"]) if pd.notnull(row["wind_speed_10m"]) else None,
                "surface_pressure": float(row["surface_pressure"]) if pd.notnull(row["surface_pressure"]) else None,
                "soil_temperature_0_to_7cm": float(row["soil_temperature_0_to_7cm"]) if pd.notnull(row["soil_temperature_0_to_7cm"]) else None,
                "soil_temperature_7_to_28cm": float(row["soil_temperature_7_to_28cm"]) if pd.notnull(row["soil_temperature_7_to_28cm"]) else None,
                "soil_moisture_0_to_7cm": float(row["soil_moisture_0_to_7cm"]) if pd.notnull(row["soil_moisture_0_to_7cm"]) else None,
                "soil_moisture_7_to_28cm": float(row["soil_moisture_7_to_28cm"]) if pd.notnull(row["soil_moisture_7_to_28cm"]) else None,
                "cloud_cover": float(row["cloud_cover"]) if pd.notnull(row["cloud_cover"]) else None,
                "acq_date": a_date,
                "acq_time": str(row.get("acq_time", "")),
                "target_date": t_date,
                "target_time": t_time_str,
                "is_forecast": is_forecast_val,
                "created_at": now,
                "updated_at": now
            })

        if not values_to_upsert:
            return 0

        # PostgreSQL ON CONFLICT (region_id, target_date, target_time) DO UPDATE
        stmt = insert(Weather).values(values_to_upsert)
        stmt = stmt.on_conflict_do_update(
            index_elements=["region_id", "target_date", "target_time"],
            set_={
                "temperature_2m": stmt.excluded.temperature_2m,
                "humidity_2m": stmt.excluded.humidity_2m,
                "precipitation": stmt.excluded.precipitation,
                "wind_speed_10m": stmt.excluded.wind_speed_10m,
                "surface_pressure": stmt.excluded.surface_pressure,
                "soil_temperature_0_to_7cm": stmt.excluded.soil_temperature_0_to_7cm,
                "soil_temperature_7_to_28cm": stmt.excluded.soil_temperature_7_to_28cm,
                "soil_moisture_0_to_7cm": stmt.excluded.soil_moisture_0_to_7cm,
                "soil_moisture_7_to_28cm": stmt.excluded.soil_moisture_7_to_28cm,
                "cloud_cover": stmt.excluded.cloud_cover,
                "acq_date": stmt.excluded.acq_date,
                "acq_time": stmt.excluded.acq_time,
                "is_forecast": stmt.excluded.is_forecast,
                "updated_at": now
            }
        )

        self.session.execute(stmt)
        self.session.commit()
        print(f"[WeatherRepository] Successfully upserted {len(values_to_upsert)} weather records.")
        return len(values_to_upsert)

    def get_weather_ids_for_forecasts(self, region_ids):
        """Returns a Pandas DataFrame containing region_id, target_date, target_time, and weather_id."""
        stmt = (
            select(
                Weather.weather_id,
                Weather.region_id,
                Weather.target_date,
                Weather.target_time,
                Weather.is_forecast
            )
            .where(
                Weather.region_id.in_(region_ids),
                Weather.is_forecast == True
            )
        )
        result = self.session.execute(stmt).fetchall()
        
        return pd.DataFrame(result, columns=["weather_id", "region_id", "target_date", "target_time", "is_forecast"])

    def get_weather_card_stats(self, region_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieves all-time min, max, avg and the most recent current reading
        for all 10 meteorological parameters.
        """
        region_clause = "WHERE region_id = :region_id" if region_id is not None else ""

        query = text(f"""
            WITH filtered_weather AS (
                SELECT *
                FROM weather
                {region_clause}
            ),
            all_time_stats AS (
                SELECT 
                    ROUND(AVG(temperature_2m)::numeric, 1) AS avg_temp,
                    ROUND(MIN(temperature_2m)::numeric, 1) AS min_temp,
                    ROUND(MAX(temperature_2m)::numeric, 1) AS max_temp,

                    ROUND(AVG(humidity_2m)::numeric, 1) AS avg_hum,
                    ROUND(MIN(humidity_2m)::numeric, 1) AS min_hum,
                    ROUND(MAX(humidity_2m)::numeric, 1) AS max_hum,

                    ROUND(AVG(precipitation)::numeric, 2) AS avg_precip,
                    ROUND(MIN(precipitation)::numeric, 2) AS min_precip,
                    ROUND(MAX(precipitation)::numeric, 2) AS max_precip,

                    ROUND(AVG(wind_speed_10m)::numeric, 1) AS avg_wind,
                    ROUND(MIN(wind_speed_10m)::numeric, 1) AS min_wind,
                    ROUND(MAX(wind_speed_10m)::numeric, 1) AS max_wind,

                    ROUND(AVG(surface_pressure)::numeric, 1) AS avg_press,
                    ROUND(MIN(surface_pressure)::numeric, 1) AS min_press,
                    ROUND(MAX(surface_pressure)::numeric, 1) AS max_press,

                    ROUND(AVG(cloud_cover)::numeric, 1) AS avg_cloud,
                    ROUND(MIN(cloud_cover)::numeric, 1) AS min_cloud,
                    ROUND(MAX(cloud_cover)::numeric, 1) AS max_cloud,

                    ROUND(AVG(soil_temperature_0_to_7cm)::numeric, 1) AS avg_soil_temp_top,
                    ROUND(MIN(soil_temperature_0_to_7cm)::numeric, 1) AS min_soil_temp_top,
                    ROUND(MAX(soil_temperature_0_to_7cm)::numeric, 1) AS max_soil_temp_top,

                    ROUND(AVG(soil_temperature_7_to_28cm)::numeric, 1) AS avg_soil_temp_deep,
                    ROUND(MIN(soil_temperature_7_to_28cm)::numeric, 1) AS min_soil_temp_deep,
                    ROUND(MAX(soil_temperature_7_to_28cm)::numeric, 1) AS max_soil_temp_deep,

                    ROUND(AVG(soil_moisture_0_to_7cm)::numeric, 3) AS avg_soil_moist_top,
                    ROUND(MIN(soil_moisture_0_to_7cm)::numeric, 3) AS min_soil_moist_top,
                    ROUND(MAX(soil_moisture_0_to_7cm)::numeric, 3) AS max_soil_moist_top,

                    ROUND(AVG(soil_moisture_7_to_28cm)::numeric, 3) AS avg_soil_moist_deep,
                    ROUND(MIN(soil_moisture_7_to_28cm)::numeric, 3) AS min_soil_moist_deep,
                    ROUND(MAX(soil_moisture_7_to_28cm)::numeric, 3) AS max_soil_moist_deep
                FROM filtered_weather
            ),
            latest_reading AS (
                SELECT *
                FROM filtered_weather
                ORDER BY target_date DESC, target_time DESC
                LIMIT 1
            )
            SELECT 
                s.*,
                l.temperature_2m AS current_temp,
                l.humidity_2m AS current_hum,
                l.precipitation AS current_precip,
                l.wind_speed_10m AS current_wind,
                l.surface_pressure AS current_press,
                l.cloud_cover AS current_cloud,
                l.soil_temperature_0_to_7cm AS current_soil_temp_top,
                l.soil_temperature_7_to_28cm AS current_soil_temp_deep,
                l.soil_moisture_0_to_7cm AS current_soil_moist_top,
                l.soil_moisture_7_to_28cm AS current_soil_moist_deep,
                l.target_date AS latest_date,
                l.target_time AS latest_time
            FROM all_time_stats s
            LEFT JOIN latest_reading l ON TRUE;
        """)

        params = {"region_id": region_id} if region_id is not None else {}
        result = self.session.execute(query, params).mappings().first()
        return dict(result) if result else {}


    def get_hourly_weather_by_date(
        self, region_id: int, target_date: date
    ) -> List[Dict[str, Any]]:
        """
        Retrieves 24 hourly weather records for a specific region and date.
        """
        stmt = (
            select(
                Weather.target_time,
                Weather.temperature_2m,
                Weather.humidity_2m,
                Weather.precipitation,
                Weather.wind_speed_10m,
                Weather.surface_pressure,
                Weather.cloud_cover
            )
            .where(
                Weather.region_id == region_id,
                Weather.target_date == target_date
            )
            .order_by(Weather.target_time.asc())
        )
        
        rows = self.session.execute(stmt).fetchall()
        return [
            {
                "target_time": str(row.target_time),
                "temperature_2m": row.temperature_2m,
                "humidity_2m": row.humidity_2m,
                "precipitation": row.precipitation,
                "wind_speed_10m": row.wind_speed_10m,
                "surface_pressure": row.surface_pressure,
                "cloud_cover": row.cloud_cover,
            }
            for row in rows
        ]

    def get_paginated_weather_table(
        self, region_id: Optional[int] = None, page: int = 1, page_size: int = 10
    ) -> List[Weather]:
        """
        Retrieves meteorological records filtered by region_id (optional), 
        ordered by acq_date and acq_time, with pagination.
        """
        offset = (page - 1) * page_size
        
        stmt = select(Weather)
        
        if region_id is not None:
            stmt = stmt.where(Weather.region_id == region_id)
            
        stmt = stmt.order_by(
            Weather.region_id.asc(),
            Weather.acq_date.desc(),
            Weather.acq_time.desc()
        ).offset(offset).limit(page_size)
        
        return list(self.session.scalars(stmt).all())

    def count_weather_records(self, region_id: Optional[int] = None) -> int:
        """
        Returns the total count of weather records matching the optional region filter.
        """
        stmt = select(func.count(Weather.weather_id))
        if region_id is not None:
            stmt = stmt.where(Weather.region_id == region_id)
            
        return self.session.scalar(stmt) or 0
    