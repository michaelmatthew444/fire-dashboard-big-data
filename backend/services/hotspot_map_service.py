import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from repositories.hotspot import HotspotRepository
from repositories.prediction import FirePredictionRepository

logger = logging.getLogger("HotspotMapService")


class HotspotMapService:
    """
    Service layer to handle fetching and formatting map visualization data
    for satellite hotspots and ML fire predictions.
    """

    def __init__(self, db: Session):
        self.db = db
        self.hotspot_repo = HotspotRepository(db)
        self.prediction_repo = FirePredictionRepository(db)

    def get_map_data(self, mode: str) -> Dict[str, Any]:
        """
        Retrieves formatted data for map visualization based on mode ('historical' or 'forecast').
        """
        if mode == "historical":
            return self._get_historical_hotspots()
        elif mode == "forecast":
            return self._get_forecast_predictions()
        else:
            logger.warning(f"Invalid mode requested: '{mode}'")
            return {"error": "Invalid mode. Supported modes: 'historical', 'forecast'."}

    def _get_historical_hotspots(self) -> Dict[str, Any]:
        """Fetches and formats max bright_ti4 satellite hotspots for the last 7 days."""
        try:
            hotspots = self.hotspot_repo.get_max_hotspots_last_7_days()
            formatted_data = [
                {
                    "region_id": h.region_id,
                    "bright_ti4": h.bright_ti4,
                    "bright_ti5": h.bright_ti5,
                    "frp": h.frp,
                    "acq_date": str(h.acq_date) if h.acq_date else None,
                    "acq_time": h.acq_time,
                    "daynight": h.daynight,
                }
                for h in hotspots
            ]
            return {"mode": "historical", "data": formatted_data}

        except Exception as e:
            logger.error(f"Error in HotspotMapService historical fetch: {e}", exc_info=True)
            raise e

    def _get_forecast_predictions(self) -> Dict[str, Any]:
        """Fetches and formats peak fire risk score predictions for the next 7 days."""
        try:
            predictions = self.prediction_repo.get_max_predictions_next_7_days()
            formatted_data = [
                {
                    "region_id": p.region_id,
                    "forecast_timestamp": p.forecast_timestamp.isoformat() if p.forecast_timestamp else None,
                    "fire_risk_score": p.fire_risk_score,
                    "is_fire_predicted": p.is_fire_predicted,
                }
                for p in predictions
            ]
            return {"mode": "forecast", "data": formatted_data}

        except Exception as e:
            logger.error(f"Error in HotspotMapService forecast fetch: {e}", exc_info=True)
            raise e