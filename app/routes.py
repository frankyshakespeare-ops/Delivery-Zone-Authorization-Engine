from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_Contains, ST_GeomFromText
from urllib3 import request
from app.database import SessionLocal
from app.models import Zone, Driver
from app.schemas import DriverCheckRequest, DriverCheckResponse

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


query = db.query(Zone).filter(ST_Contains(Zone.geom, point))
if request.current_time:
    query = query.filter(
        (Zone.valid_from <= request.current_time) | (Zone.valid_from.is_(None)),
        (Zone.valid_to >= request.current_time) | (Zone.valid_to.is_(None))
    )
if request.weather:
    query = query.filter((Zone.weather_condition == request.weather) | (Zone.weather_condition.is_(None)))
# etc.


@router.post("/can_accept_order", response_model=DriverCheckResponse)
def can_accept_order(request: DriverCheckRequest, db: Session = Depends(get_db)):
    # Créer un point au format WKT
    point_wkt = f"POINT({request.lon} {request.lat})"
    point = ST_GeomFromText(point_wkt, 4326)

    # Vérifier si le point est dans au moins une zone
    zone = db.query(Zone).filter(ST_Contains(Zone.geom, point)).first()
    authorized = zone is not None

    # Mettre à jour la position du driver
    driver = db.query(Driver).filter(Driver.id == request.driver_id).first()
    if driver:
        driver.last_position = point
    else:
        new_driver = Driver(id=request.driver_id, last_position=point)
        db.add(new_driver)
    db.commit()

    return DriverCheckResponse(authorized=authorized)