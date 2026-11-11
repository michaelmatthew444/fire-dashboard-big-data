import pandas as pd
from datetime import datetime
from database import SessionLocal
from repositories import RegionRepository, WeatherRepository, FirePredictionRepository
from fetchers.meteo_fetcher import OpenMeteoFetcher
from services.ml_service import predict_fire_risk


def test_openmeteo_fetcher():
    session = SessionLocal()

    try:
        print("[test_openmeteo] Initializing OpenMeteoFetcher...")
        fetcher = OpenMeteoFetcher(session)
        region_repo = RegionRepository(session)
        weather_repo = WeatherRepository(session)
        pred_repo = FirePredictionRepository(session)
        start_time = datetime.now()

        all_regions = region_repo.get_all()
        if not all_regions:
            print("[test_openmeteo] No regions found in database.")
            return

        # 1. Target range: 2026-09-09 to 2026-09-13
        target_start_date = "2026-09-09"
        target_end_date = "2026-09-13"

        print(f"[test_openmeteo] Fetching historical weather from {target_start_date} to {target_end_date}...")
        df_weather = fetcher.fetch_weather_for_regions(
            grid_precision=1.0,
            batch_size=100,
            mode="historical",
            start_date=target_start_date,
            end_date=target_end_date,
            regions=all_regions
        )

        duration = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 50)
        print(" TEST RESULTS")
        print("=" * 50)
        print(f"Total Execution Time: {duration:.2f} seconds")

        if df_weather.empty:
            print("[FAIL] Returned DataFrame is EMPTY.")
            return

        print(f"[SUCCESS] Successfully mapped weather data for {len(df_weather)} records!")

        # 2. Force is_forecast = True for 2026-09-13 records
        df_weather["target_date_str"] = df_weather["target_date"].astype(str)
        mask_target_date = df_weather["target_date_str"] == target_end_date

        df_weather.loc[mask_target_date, "is_forecast"] = True
        df_weather.drop(columns=["target_date_str"], inplace=True)

        print(
            f"[test_openmeteo] Overrode is_forecast=True for {mask_target_date.sum()} records on date {target_end_date}."
        )

        # 3. Upsert weather records into PostgreSQL
        print(f"[test_openmeteo] Attempting to upsert {len(df_weather)} weather records into the database...")
        upserted_count = weather_repo.upsert_weather(df_weather)
        print(f"[test_openmeteo] Successfully upserted {upserted_count} weather records.")

        # 4. Extract in-memory forecast records (for 2026-09-13)
        df_forecast_only = df_weather[df_weather["is_forecast"] == True].copy()

        if not df_forecast_only.empty:
            unique_region_ids = df_forecast_only["region_id"].unique().tolist()
            df_db_weather = weather_repo.get_weather_ids_for_forecasts(unique_region_ids)

            if df_db_weather is not None and not df_db_weather.empty:
                df_forecast_only["target_date"] = df_forecast_only["target_date"].astype(str)
                df_db_weather["target_date"] = df_db_weather["target_date"].astype(str)
                df_forecast_only["target_time"] = df_forecast_only["target_time"].astype(str)
                df_db_weather["target_time"] = df_db_weather["target_time"].astype(str)

                # Merge weather_id cleanly
                df_forecast_only = df_forecast_only.merge(
                    df_db_weather[["region_id", "target_date", "target_time", "weather_id"]],
                    on=["region_id", "target_date", "target_time"],
                    how="inner"
                )

            # 5. Pass forecast DataFrame directly to PySpark ML Service
            print(f"\n[test_openmeteo] Passing {len(df_forecast_only)} forecast rows with weather_ids to Spark ML pipeline...")
            df_predictions_spark = predict_fire_risk(df_forecast_only)
            print("[test_openmeteo] PySpark ML prediction pipeline completed successfully.")

            # 6. Upsert PySpark ML predictions into fire_prediction table
            if df_predictions_spark is not None:
                saved_count = pred_repo.upsert_predictions(df_predictions_spark)
                print(f"[test_openmeteo] Successfully upserted {saved_count} fire predictions into database.")
        else:
            print("\n[test_openmeteo] No forecast records found for target date. Skipping ML predictions.")

    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()
        print("\n[test_openmeteo] Session closed.")


if __name__ == "__main__":
    test_openmeteo_fetcher()