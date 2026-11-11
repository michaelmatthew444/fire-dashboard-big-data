from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from models.hotspot import Hotspot
from datetime import datetime, date, timedelta
import pandas as pd
from typing import List, Optional


class HotspotRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, hotspot_id: int) -> Hotspot | None:
        return self.session.get(Hotspot, hotspot_id)

    def get_by_region(self, region_id: int) -> list[Hotspot]:
        stmt = select(Hotspot).where(Hotspot.region_id == region_id)
        return list(self.session.scalars(stmt).all())

    def create(self, region_id: int, bright_ti4: float, bright_ti5: float, frp: float, acq_date, acq_time: str, daynight: str) -> Hotspot:
        hotspot = Hotspot(
            region_id=region_id,
            bright_ti4=bright_ti4,
            bright_ti5=bright_ti5,
            frp=frp,
            acq_date=acq_date,
            acq_time=acq_time,
            daynight=daynight
        )
        self.session.add(hotspot)
        self.session.commit()
        self.session.refresh(hotspot)
        return hotspot

    def upsert_hotspots(self, df_hotspots: pd.DataFrame) -> list[Hotspot]:
        """
        Upsert hotspots from a DataFrame into the database.
        If a hotspot with the same region_id and acq_date exists, update it; otherwise, insert a new record.
        """
        if df_hotspots is None or df_hotspots.empty:
            print("[HotspotRepository] No hotspot records provided for ingestion.")
            return 0

        values_to_upsert = []
        for _, row in df_hotspots.iterrows():
            acq_d = row["acq_date"]
            if isinstance(acq_d, str):
                acq_d = datetime.strptime(acq_d, "%Y-%m-%d").date()

            values_to_upsert.append({
                "region_id": int(row["region_id"]),
                "bright_ti4": float(row["bright_ti4"]),
                "bright_ti5": float(row["bright_ti5"]),
                "frp": float(row["frp"]),
                "acq_date": acq_d,
                "acq_time": str(row["acq_time"]),
                "daynight": str(row["daynight"])
            })

        if not values_to_upsert:
            return 0

        # PostgreSQL ON CONFLICT DO UPDATE
        stmt = insert(Hotspot).values(values_to_upsert)
        stmt = stmt.on_conflict_do_update(
            index_elements=["region_id", "acq_date", "acq_time"],  # Constraint columns
            set_={
                "bright_ti4": stmt.excluded.bright_ti4,
                "bright_ti5": stmt.excluded.bright_ti5,
                "frp": stmt.excluded.frp,
                "daynight": stmt.excluded.daynight
            }
        )

        self.session.execute(stmt)
        self.session.commit()
        print(f"[HotspotRepository] Successfully upserted {len(values_to_upsert)} records.")
        return len(values_to_upsert)


    def get_max_hotspots_last_7_days(self) -> List[Hotspot]:
        """
        Retrieves hotspot records from today down to 7 days ago.
        Groups by (region_id, acq_date) and selects the record with the 
        highest bright_ti4 temperature for each region on each day.
        """
        today = date.today()
        start_date = today - timedelta(days=7)

        # 1. Subquery to calculate max bright_ti4 per region per day
        subquery = (
            self.session.query(
                Hotspot.region_id,
                Hotspot.acq_date,
                func.max(Hotspot.bright_ti4).label("max_bright_ti4")
            )
            .filter(Hotspot.acq_date >= start_date)
            .filter(Hotspot.acq_date <= today)
            .group_by(Hotspot.region_id, Hotspot.acq_date)
            .subquery()
        )

        # 2. Join back to full Hotspot table to extract complete record attributes
        records = (
            self.session.query(Hotspot)
            .join(
                subquery,
                (Hotspot.region_id == subquery.c.region_id) &
                (Hotspot.acq_date == subquery.c.acq_date) &
                (Hotspot.bright_ti4 == subquery.c.max_bright_ti4)
            )
            .order_by(Hotspot.acq_date.desc(), Hotspot.region_id)
            .all()
        )

        return records
    
    def get_paginated_hotspot_table(
            self, region_id: Optional[int] = None, page: int = 1, page_size: int = 10
        ) -> List[Hotspot]:
        """
        Retrieves Hotspot records filtered by region_id (optional), 
        ordered by acq_date and acq_time, with pagination.
        """
        offset = (page - 1) * page_size
        
        stmt = select(Hotspot)
        
        if region_id is not None:
            stmt = stmt.where(Hotspot.region_id == region_id)
            
        stmt = stmt.order_by(
            Hotspot.region_id.asc(),
            Hotspot.acq_date.desc(),
            Hotspot.acq_time.desc()
        ).offset(offset).limit(page_size)
            
        return list(self.session.scalars(stmt).all())
    
    def count_hotspot_records(self, region_id: Optional[int] = None) -> int:
        """
        Returns the total count of hotspot records matching the optional region filter.
        """
        stmt = select(func.count(Hotspot.hotspot_id))
        if region_id is not None:
            stmt = stmt.where(Hotspot.region_id == region_id)
            
        return self.session.scalar(stmt) or 0