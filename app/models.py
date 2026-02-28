from sqlalchemy import Column, Float, Integer, String, DateTime, func
from geoalchemy2 import Geometry
from app.database import Base

class Zone(Base):
    __tablename__ = "zones"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)
    # Pour les zones dynamiques (V2)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    weather_condition = Column(String, nullable=True)   # ex: "rain", "clear"
    congestion_level = Column(Integer, nullable=True)   # 1-5

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    last_position = Column(Geometry("POINT", srid=4326), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Order(Base):   # Pour la V3 (clustering)
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
    # On stocke la forme de la zone (le polygone)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)
    # On stocke quelques métriques pour l'analyse
    order_count = Column(Integer)
    surge_multiplier = Column(Float, default=1.5)
    # L'heure à laquelle le hotspot a été détecté
    created_at = Column(DateTime, server_default=func.now())