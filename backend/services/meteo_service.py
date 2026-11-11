import logging
import pandas as pd
from typing import Optional, List
from sqlalchemy.orm import Session

from fetchers.meteo_fetcher import OpenMeteoFetcher
from repositories.region import RegionRepository
from repositories.weather import WeatherRepository
from repositories.prediction import FirePredictionRepository
from services.ml_service import predict_fire_risk

logger = logging.getLogger("MeteoService")


class MeteoService:
    """
    Service orchestrating Open-Meteo weather data fetching, database upserting,
    and PySpark ML fire risk classification.
    """

    def __init__(self, session: Session):
        self.session = session
        self.region_repo = RegionRepository(session)
        self.weather_repo = WeatherRepository(session)
        self.pred_repo = FirePredictionRepository(session)
        self.fetcher = OpenMeteoFetcher(session)

    def run_meteo_pipeline(
        self,
        grid_precision: float = 1.0,
        batch_size: int = 100,
        forecast_days: int = 3,
        past_days: int = 0,
        regions: Optional[List] = None,
    ) -> dict:
        """
        Executes the end-to-end weather ingestion and fire prediction pipeline:
        1. Retrieves regions from DB (or uses provided regions).
        2. Fetches weather metrics from Open-Meteo API.
        3. Upserts weather records into PostgreSQL.
        4. Retrieves generated weather_ids for forecast records.
        5. Runs PySpark ML fire risk classification.
        6. Upserts predictions into PostgreSQL.

        Returns a dictionary containing summary counts.
        """
        # 1. Load regions
        if regions is None:
            all_regions = self.region_repo.get_all()
        else:
            all_regions = regions

        if not all_regions:
            logger.warning("[MeteoService] No valid regions provided or found in database.")
            return {"weather_upserted": 0, "predictions_upserted": 0}

        logger.info(f"[MeteoService] Loaded {len(all_regions)} regions. Fetching Open-Meteo weather data...")

        # 2. Fetch weather metrics
        df_weather = self.fetcher.fetch_weather_for_regions(
            grid_precision=grid_precision,
            batch_size=batch_size,
            forecast_days=forecast_days,
            past_days=past_days,
            regions=all_regions,
        )

        if df_weather is None or df_weather.empty:
            logger.info("[MeteoService] Returned weather DataFrame is empty. Pipeline halted.")
            return {"weather_upserted": 0, "predictions_upserted": 0}

        # 3. Upsert weather into DB
        logger.info(f"[MeteoService] Upserting {len(df_weather)} weather records into database...")
        weather_count = self.weather_repo.upsert_weather(df_weather)
        logger.info(f"[MeteoService] Successfully upserted {weather_count} weather records.")

        # 4. Filter forecast records and map weather_ids from database
        unique_region_ids = df_weather["region_id"].unique().tolist()
        df_db_weather = self.weather_repo.get_weather_ids_for_forecasts(unique_region_ids)

        df_forecast_only = df_weather[df_weather["is_forecast"] == True].copy()

        if df_forecast_only.empty:
            logger.info("[MeteoService] No forecast records found (is_forecast == True). Skipping ML predictions.")
            return {"weather_upserted": weather_count, "predictions_upserted": 0}

        # Align data types for joining
        df_forecast_only["target_date"] = df_forecast_only["target_date"].astype(str)
        df_forecast_only["target_time"] = df_forecast_only["target_time"].astype(str)
        df_db_weather["target_date"] = df_db_weather["target_date"].astype(str)
        df_db_weather["target_time"] = df_db_weather["target_time"].astype(str)

        df_forecast_only = df_forecast_only.merge(
            df_db_weather[["region_id", "target_date", "target_time", "weather_id"]],
            on=["region_id", "target_date", "target_time"],
            how="inner",
        )

        # 5. Execute Spark ML Inference
        logger.info(f"[MeteoService] Passing {len(df_forecast_only)} forecast rows to PySpark ML pipeline...")
        df_predictions_spark = predict_fire_risk(df_forecast_only)

        if df_predictions_spark is None:
            logger.warning("[MeteoService] ML inference returned None.")
            return {"weather_upserted": weather_count, "predictions_upserted": 0}

        # 6. Upsert Predictions into PostgreSQL
        predictions_count = self.pred_repo.upsert_predictions(df_predictions_spark)
        logger.info(f"[MeteoService] Successfully upserted {predictions_count} predictions into database.")

        return {
            "weather_upserted": weather_count,
            "predictions_upserted": predictions_count,
        }