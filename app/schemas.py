from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class DriverCheckRequest(BaseModel):
    driver_id: int
    lat: float
    lon: float
    current_time: Optional[datetime] = None
    weather: Optional[str] = None
    congestion_tolerance: Optional[int] = None

class DriverCheckResponse(BaseModel):
    authorized: bool