from datetime import datetime
from sqlalchemy import Column, Integer, Double, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base

class FirePrediction(Base):
    __tablename__ = 'fire_prediction'

    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    region_id = Column(Integer, ForeignKey('region.region_id', ondelete='CASCADE'), nullable=False)
    weather_id = Column(Integer, ForeignKey('weather.weather_id', ondelete='CASCADE'), nullable=False)
    forecast_timestamp = Column(DateTime)
    fire_risk_score = Column(Double)
    is_fire_predicted = Column(Double)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('region_id', 'forecast_timestamp', name='uq_prediction_region_forecast_timestamp'),
    )

    # Make sure this 'region' property exists!
    region = relationship("Region", back_populates="predictions")
    weather = relationship("Weather", back_populates="predictions")