import sys
from pathlib import Path

# Add backend root directory to sys.path
FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]  # Points to 'backend' directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from datetime import datetime
from sqlalchemy import Column, Integer, Double, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base

class Hotspot(Base):
    __tablename__ = 'hotspot'

    hotspot_id = Column(Integer, primary_key=True, autoincrement=True)
    region_id = Column(Integer, ForeignKey('region.region_id', ondelete='CASCADE'), nullable=False)
    bright_ti4 = Column(Double)
    acq_date = Column(Date)
    acq_time = Column(String(10))
    bright_ti5 = Column(Double)
    frp = Column(Double)
    daynight = Column(String(1))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Composite Unique Constraint required for PostgreSQL ON CONFLICT DO UPDATE
    __table_args__ = (
        UniqueConstraint('region_id', 'acq_date', 'acq_time', name='uq_region_acq_date_time'),
    )

    region = relationship("Region", back_populates="hotspots")