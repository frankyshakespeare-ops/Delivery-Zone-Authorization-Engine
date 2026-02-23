from pydantic import BaseModel

class DriverCheckRequest(BaseModel):
    driver_id: int
    lat: float
    lon: float

class DriverCheckResponse(BaseModel):
    authorized: bool