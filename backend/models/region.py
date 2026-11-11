from datetime import datetime
from sqlalchemy import Column, Integer, Double, DateTime
from sqlalchemy.orm import relationship
from models.base import Base

class Region(Base):
    __tablename__ = 'region'

    region_id = Column(Integer, primary_key=True, autoincrement=True)
    centroid_longitude = Column(Double, nullable=True)
    centroid_latitude = Column(Double, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    hotspots = relationship("Hotspot", back_populates="region", cascade="all, delete-orphan")
    weathers = relationship("Weather", back_populates="region", cascade="all, delete-orphan")
    predictions = relationship("FirePrediction", back_populates="region", cascade="all, delete-orphan")