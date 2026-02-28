from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import ST_Contains, ST_GeomFromText
import numpy as np
from sklearn.cluster import DBSCAN

# Imports internes
from app.database import get_db
from app.models import Zone, Driver, Order
from app.schemas import DriverCheckRequest, DriverCheckResponse

router = APIRouter()

# --- Endpoint 1 : Vérification d'autorisation ---
@router.post("/can_accept_order", response_model=DriverCheckResponse)
def can_accept_order(request: DriverCheckRequest, db: Session = Depends(get_db)):
    # 1. Créer le point géographique
    point_wkt = f"POINT({request.lon} {request.lat})"
    point = ST_GeomFromText(point_wkt, 4326)

    # 2. Logique de filtrage (V2 - Temps et Météo si présents)
    query = db.query(Zone).filter(ST_Contains(Zone.geom, point))
    
    # Note: On utilise getattr pour éviter de planter si les champs ne sont pas dans le schema
    current_time = getattr(request, 'current_time', None)
    weather = getattr(request, 'weather', None)

    if current_time:
        query = query.filter(
            (Zone.valid_from <= current_time) | (Zone.valid_from.is_(None)),
            (Zone.valid_to >= current_time) | (Zone.valid_to.is_(None))
        )
    if weather:
        query = query.filter((Zone.weather_condition == weather) | (Zone.weather_condition.is_(None)))

    zone = query.first()
    authorized = zone is not None

    # 3. Mettre à jour la position du driver
    driver = db.query(Driver).filter(Driver.id == request.driver_id).first()
    if driver:
        driver.last_position = point
    else:
        new_driver = Driver(id=request.driver_id, last_position=point)
        db.add(new_driver)
    
    db.commit()
    return DriverCheckResponse(authorized=authorized)

# --- Endpoint 2 : Clustering des commandes (V3) ---
@router.get("/clustering/orders")
def cluster_orders(eps: float = 0.001, min_samples: int = 3, db: Session = Depends(get_db)):
    # 1. Récupérer les coordonnées via PostGIS (ST_X, ST_Y)
    orders_query = db.query(
        Order.id,
        func.ST_X(Order.position).label("lon"),
        func.ST_Y(Order.position).label("lat")
    ).all()

    if not orders_query:
        return {"total_orders": 0, "clusters": []}

    # 2. Préparer les données pour Scikit-Learn
    coords = np.array([[o.lon, o.lat] for o in orders_query])

    # 3. Appliquer DBSCAN
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    labels = clustering.labels_

    # 4. Organiser les résultats
    results = []
    for i, order in enumerate(orders_query):
        results.append({
            "order_id": order.id,
            "lon": order.lon,
            "lat": order.lat,
            "cluster_id": int(labels[i])  # Conversion numpy -> int pour JSON
        })

    return {
        "total_orders": len(results),
        "clusters_found": len(set(labels)) - (1 if -1 in labels else 0),
        "data": results
    }