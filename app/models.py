from sqlalchemy import Column, Float, Integer, String, DateTime, func
from geoalchemy2 import Geometry
from app.database import Base

class Zone(Base):
    __tablename__ = "zones"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, default="delivery")
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)
    # For dynamic areas (V2)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    weather_condition = Column(String, nullable=True)   # ex: "rain", "clear"
    congestion_level = Column(Integer, nullable=True)   # 1-5

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    last_position = Column(Geometry("POINT", srid=4326), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Order(Base):   # For V3 (clustering)
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    position = Column(Geometry("POINT", srid=4326), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())

class Hotspot(Base):
    __tablename__ = "hotspots"
    
    id = Column(Integer, primary_key=True, index=True)
    # We store the shape of the area (the polygon)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)
    # The number of orders detected in this hotspot area during the last time window
    order_count = Column(Integer)
    surge_multiplier = Column(Float, default=1.5)
    # The time at which the hotspot was detected
    created_at = Column(DateTime, server_default=func.now())