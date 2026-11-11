from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from models.prediction import FirePrediction


class FirePredictionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, prediction_id: int) -> FirePrediction | None:
        return self.session.get(FirePrediction, prediction_id)

    def create(self, region_id: int, weather_id: int, score: float, is_predicted: float, forecast_time) -> FirePrediction:
        pred = FirePrediction(
            region_id=region_id,
            weather_id=weather_id,
            fire_risk_score=score,
            is_fire_predicted=is_predicted,
            forecast_timestamp=forecast_time
        )
        self.session.add(pred)
        self.session.commit()
        self.session.refresh(pred)
        return pred

    def upsert_predictions(self, df_predictions) -> int:
        """
        Upserts fire prediction records into the database.
        Accepts either a Pandas DataFrame or a PySpark DataFrame.
        """
        if df_predictions is None:
            print("[PredictionRepository] No predictions passed. Skipping.")
            return 0

        # Convert PySpark DataFrame to Pandas if necessary
        if hasattr(df_predictions, "toPandas"):
            df_predictions_pandas = df_predictions.toPandas()
        else:
            df_predictions_pandas = df_predictions

        if df_predictions_pandas.empty:
            print("[PredictionRepository] Empty DataFrame passed. Skipping.")
            return 0

        # Convert DataFrame to a list of dicts for SQLAlchemy execution
        records = df_predictions_pandas.to_dict(orient="records")

        # Build PostgreSQL INSERT statement
        stmt = insert(FirePrediction).values(records)

        # Define update values for conflicting rows
        update_dict = {
            "fire_risk_score": stmt.excluded.fire_risk_score,
            "is_fire_predicted": stmt.excluded.is_fire_predicted,
            "updated_at": stmt.excluded.updated_at,
        }

        # Dynamically include weather_id if present in incoming records
        if "weather_id" in records[0]:
            update_dict["weather_id"] = stmt.excluded.weather_id

        # Upsert rule matching the unique constraint on (region_id, forecast_timestamp)
        upsert_stmt = stmt.on_conflict_do_update(
            constraint="uq_prediction_region_forecast_timestamp",
            set_=update_dict,
        )

        try:
            self.session.execute(upsert_stmt)
            self.session.commit()
            print(f"[PredictionRepository] Successfully upserted {len(records)} prediction records.")
            return len(records)
        except Exception as e:
            self.session.rollback()
            print(f"[PredictionRepository] Error during prediction upsert: {e}")
            raise e

    def get_max_predictions_next_7_days(self) -> List[FirePrediction]:
        """
        Retrieves fire prediction records from tomorrow until 7 days from now.
        Groups by (region_id, forecast_date), selecting the highest fire_risk_score 
        for each region ON EACH DAY.
        """
        tomorrow = date.today() + timedelta(days=1)
        end_date = date.today() + timedelta(days=7)

        start_ts = datetime.combine(tomorrow, datetime.min.time())
        end_ts = datetime.combine(end_date, datetime.max.time())

        # Extract date from timestamp for grouping
        forecast_date = func.date(FirePrediction.forecast_timestamp)

        # 1. Subquery: Max risk score per region PER DAY
        subquery = (
            self.session.query(
                FirePrediction.region_id,
                forecast_date.label("f_date"),
                func.max(FirePrediction.fire_risk_score).label("max_risk_score")
            )
            .filter(FirePrediction.forecast_timestamp >= start_ts)
            .filter(FirePrediction.forecast_timestamp <= end_ts)
            .group_by(FirePrediction.region_id, forecast_date)
            .subquery()
        )

        # 2. Join back to get full record details
        records = (
            self.session.query(FirePrediction)
            .join(
                subquery,
                (FirePrediction.region_id == subquery.c.region_id) &
                (func.date(FirePrediction.forecast_timestamp) == subquery.c.f_date) &
                (FirePrediction.fire_risk_score == subquery.c.max_risk_score)
            )
            .order_by(FirePrediction.forecast_timestamp.asc(), FirePrediction.fire_risk_score.desc())
            .all()
        )

        return records

    