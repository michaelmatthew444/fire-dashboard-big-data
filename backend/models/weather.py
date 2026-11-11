from datetime import datetime
from sqlalchemy import Column, Integer, Double, String, Date, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base

class Weather(Base):
    __tablename__ = 'weather'

    weather_id = Column(Integer, primary_key=True, autoincrement=True)
    region_id = Column(Integer, ForeignKey('region.region_id', ondelete='CASCADE'), nullable=False)
    temperature_2m = Column(Double)
    humidity_2m = Column(Double)
    precipitation = Column(Double)
    wind_speed_10m = Column(Double)
    surface_pressure = Column(Double)
    soil_temperature_0_to_7cm = Column(Double)
    soil_temperature_7_to_28cm = Column(Double)
    soil_moisture_0_to_7cm = Column(Double)
    soil_moisture_7_to_28cm = Column(Double)
    cloud_cover = Column(Double)
    acq_date = Column(Date)
    acq_time = Column(String(10))
    target_date = Column(Date)
    target_time = Column(String(10))
    is_forecast = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique Constraint for UPSERT operations
    __table_args__ = (
        UniqueConstraint('region_id', 'target_date', 'target_time', name='uq_weather_region_target_date_time'),
    )

    region = relationship("Region", back_populates="weathers")
    predictions = relationship("FirePrediction", back_populates="weather", cascade="all, delete-orphan")