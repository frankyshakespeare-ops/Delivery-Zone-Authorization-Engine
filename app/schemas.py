from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class DriverCheckRequest(BaseModel):
    driver_id: int
    lat: float
    lon: float
    current_time: Optional[datetime] = None
    weather: Optional[str] = None
    # Optionnel pour de futures évolutions (V4)
    congestion_tolerance: Optional[int] = None

class DriverCheckResponse(BaseModel):
    authorized: bool
    # Nouveaux champs pour la tarification dynamique
    surge_active: bool = False
    multiplier: float = 1.0