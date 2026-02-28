from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class DriverCheckRequest(BaseModel):
    driver_id: int
    lat: float
    lon: float
    current_time: Optional[datetime] = None
    weather: Optional[str] = None
    # Optional for future developments (V4)
    congestion_tolerance: Optional[int] = None

class DriverCheckResponse(BaseModel):
    authorized: bool
    # New fields for dynamic pricing
    surge_active: bool = False
    multiplier: float = 1.0