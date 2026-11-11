from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import select, text
from models.region import Region

class RegionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, region_id: int) -> Region | None:
        return self.session.get(Region, region_id)

    def get_all(self, limit: int = 100) -> list[Region]:
        return list(self.session.scalars(select(Region).limit(limit)).all())

    def get_all(self) -> list[Region]:
        return list(self.session.scalars(select(Region)).all())

    def create(self, lat: float, lon: float) -> Region:
        region = Region(centroid_latitude=lat, centroid_longitude=lon)
        self.session.add(region)
        self.session.commit()
        self.session.refresh(region)
        return region

    def update(self, region_id: int, lat: float = None, lon: float = None) -> Region | None:
        region = self.get_by_id(region_id)
        if not region:
            return None
        if lat is not None:
            region.centroid_latitude = lat
        if lon is not None:
            region.centroid_longitude = lon
        self.session.commit()
        self.session.refresh(region)
        return region

    def delete(self, region_id: int) -> bool:
        region = self.get_by_id(region_id)
        if region:
            self.session.delete(region)
            self.session.commit()
            return True
        return False

    def find_nearest_region(self, lat: float, lon: float) -> Region | None:
        """
        Finds the closest region_id out of the 66,768 regions 
        for a given target latitude and longitude.
        """
        sql = text("""
            SELECT region_id 
            FROM region 
            ORDER BY ((centroid_latitude - :lat)^2 + (centroid_longitude - :lon)^2) ASC 
            LIMIT 1;
        """)
        result = self.session.execute(sql, {"lat": lat, "lon": lon}).fetchone()
        
        if result:
            return self.get_by_id(result.region_id)
        return None

    def get_all_region_ids(self) -> List[int]:
        stmt = select(Region.region_id)
        return list(self.session.scalars(stmt).all())
    