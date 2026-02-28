from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import ST_Contains, ST_GeomFromText
import numpy as np
from sklearn.cluster import DBSCAN
from geoalchemy2.functions import ST_ConvexHull, ST_Collect, ST_Centroid, ST_AsGeoJSON
import json
from app.models import Hotspot
from sqlalchemy import not_
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping


# Internal imports
from app.database import get_db
from app.models import Zone, Driver, Order
from app.schemas import DriverCheckRequest, DriverCheckResponse

router = APIRouter()

# Helper to calculate the current heat zone
def get_current_surge_zone(db: Session):
    """Calcule la zone de chaleur actuelle à partir des commandes."""
    # we explicitly ask for the values X and Y from the database
    orders_data = db.query(
        Order.id,
        func.ST_X(Order.position).label("lon"),
        func.ST_Y(Order.position).label("lat")
    ).all()

    if len(orders_data) < 5:
        return None
    
    # We transform the results into a NumPy array of FLOATS
    coords = np.array([[float(o.lon), float(o.lat)] for o in orders_data])
    
    # Now DBSCAN will work because it receives numbers, not strings
    clustering = DBSCAN(eps=0.002, min_samples=5).fit(coords)
    
    unique_labels, counts = np.unique(clustering.labels_[clustering.labels_ >= 0], return_counts=True)
    if len(unique_labels) == 0:
        return None
        
    top_cluster_id = unique_labels[np.argmax(counts)]
    top_order_ids = [orders_data[i].id for i, label in enumerate(clustering.labels_) if label == top_cluster_id]
    
    return db.query(func.ST_ConvexHull(func.ST_Collect(Order.position)))\
             .filter(Order.id.in_(top_order_ids)).scalar()

# --- Endpoint 1 : Check si le driver peut accepter une commande (V3) ---
@router.post("/can_accept_order", response_model=DriverCheckResponse)
def can_accept_order(request: DriverCheckRequest, db: Session = Depends(get_db)):
    # 1. Create the delivery person's geographic point
    point_wkt = f"POINT({request.lon} {request.lat})"
    point = ST_GeomFromText(point_wkt, 4326)

    # 2. Check if the point is within any active zone (considering time and weather conditions)
    query = db.query(Zone).filter(ST_Contains(Zone.geom, point))
    
    current_time = getattr(request, 'current_time', None)
    weather = getattr(request, 'weather', None)

    if current_time:
        query = query.filter((Zone.valid_from <= current_time) | (Zone.valid_from.is_(None)),
                             (Zone.valid_to >= current_time) | (Zone.valid_to.is_(None)))
    if weather:
        query = query.filter((Zone.weather_condition == weather) | (Zone.weather_condition.is_(None)))

    zone = query.first()
    authorized = zone is not None

    # 3. Check if the driver is in a surge zone
    surge_active = False
    surge_zone_geom = get_current_surge_zone(db) # Retrieve the geometry of the current heat cluster
    
    if surge_zone_geom:
        # Check if the driver's point is within the surge zone geometry
        is_in_surge = db.query(func.ST_Contains(surge_zone_geom, point)).scalar()
        surge_active = bool(is_in_surge)

    # 4. Update the driver's last position in the database (or create a new record if it doesn't exist)
    driver = db.query(Driver).filter(Driver.id == request.driver_id).first()
    if driver:
        driver.last_position = point
    else:
        new_driver = Driver(id=request.driver_id, last_position=point)
        db.add(new_driver)
    
    db.commit()

    # A SINGLE RETURN at the end with all the info
    return DriverCheckResponse(
        authorized=authorized,
        surge_active=surge_active,
        multiplier=1.5 if surge_active else 1.0
    )

# --- Endpoint 2 : Order clustering to identify hot spots (V1) ---
@router.get("/clustering/orders")
def cluster_orders(eps: float = 0.001, min_samples: int = 3, db: Session = Depends(get_db)):
    # 1. Retrieve coordinates via PostGIS (ST_X, ST_Y)
    orders_query = db.query(
        Order.id,
        func.ST_X(Order.position).label("lon"),
        func.ST_Y(Order.position).label("lat")
    ).all()

    if not orders_query:
        return {"total_orders": 0, "clusters": []}

    # 2. Transform the results into a NumPy array of FLOATS (DBSCAN needs numbers, not strings)
    coords = np.array([[o.lon, o.lat] for o in orders_query])

    # 3. Apply DBSCAN clustering
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    labels = clustering.labels_

    # 4. Prepare the results for JSON response (convert numpy types to native Python types)
    results = []
    for i, order in enumerate(orders_query):
        results.append({
            "order_id": order.id,
            "lon": order.lon,
            "lat": order.lat,
            "cluster_id": int(labels[i])  # Convert numpy int to native int for JSON serialization
        })

    return {
        "total_orders": len(results),
        "clusters_found": len(set(labels)) - (1 if -1 in labels else 0),
        "data": results
    }


# --- Endpoint 3: Dynamic Bonus Zone (V1) ---
@router.get("/heatmap/top-cluster")
def get_dynamic_hotspot(db: Session = Depends(get_db)):
    """
    Identifie le cluster le plus dense et génère une zone dynamique (Polygone).
    """
    # 1. Retrieves the clustering data (we reuse the previous logic)
    orders_query = db.query(
        Order.id,
        Order.position,
        func.ST_X(Order.position).label("lon"),
        func.ST_Y(Order.position).label("lat")
    ).all()

    if not orders_query:
        return {"message": "Aucune commande disponible"}

    coords = np.array([[o.lon, o.lat] for o in orders_query])
    # eps=0.002 (env 200m), min_samples=5 To find a real dense area
    clustering = DBSCAN(eps=0.002, min_samples=5).fit(coords)
    labels = clustering.labels_

    # 2. Identify the most dense cluster (the one with the most points, excluding noise)
    unique_labels, counts = np.unique(labels[labels >= 0], return_counts=True)
    if len(unique_labels) == 0:
        return {"message": "Aucun hotspot détecté pour le moment"}
    
    top_cluster_id = unique_labels[np.argmax(counts)]

    # 3. Retrieve the IDs of the orders that belong to the winning cluster
    top_order_ids = [orders_query[i].id for i, label in enumerate(labels) if label == top_cluster_id]

    # 4. Generate the Polygon with PostGIS
    # ST_Collect groups the points, ST_ConvexHull creates the envelope, ST_AsGeoJSON converts to GeoJSON format
    hotspot_geom = db.query(
        func.ST_AsGeoJSON(
            func.ST_ConvexHull(
                func.ST_Collect(Order.position)
            )
        ).label("geojson"),
        func.ST_AsGeoJSON(
            func.ST_Centroid(
                func.ST_Collect(Order.position)
            )
        ).label("center")
    ).filter(Order.id.in_(top_order_ids)).first()

    return {
        "cluster_id": int(top_cluster_id),
        "order_count": int(max(counts)),
        "type": "DYNAMIC_SURGE_ZONE",
        "geometry": json.loads(hotspot_geom.geojson),
        "center": json.loads(hotspot_geom.center),
        "suggested_multiplier": 1.5  # This can be dynamic based on the order count or other factors in a real implementation
    }

# --- Endpoint 4: Dynamic Bonus Zone with History (V2) ---
@router.get("/heatmap/surge-zone")
def get_surge_zone(db: Session = Depends(get_db)):
    """
    Identifie le cluster le plus dense et génère une zone de bonus dynamique.
    """
  # 1. Retrieves the clustering data (we reuse the previous logic, but we ensure to get the coordinates as floats for DBSCAN)
    orders_data = db.query(
        Order.id,
        func.ST_X(Order.position).label("lon"),
        func.ST_Y(Order.position).label("lat")
    ).all()

    if len(orders_data) < 5:
        return {"active": False, "message": "Pas assez de commandes pour un cluster"}

    # 2. Transform the results into a NumPy array of FLOATS (DBSCAN needs numbers, not strings)
    # convert to float here to avoid any issues with data types that could cause DBSCAN to fail
    coords = np.array([[float(o.lon), float(o.lat)] for o in orders_data])

    
    clustering = DBSCAN(eps=0.002, min_samples=5).fit(coords)
    
    unique_labels, counts = np.unique(clustering.labels_[clustering.labels_ >= 0], return_counts=True)
    if len(unique_labels) == 0:
        return {"active": False, "message": "Aucun cluster dense détecté"}

    top_cluster_id = unique_labels[np.argmax(counts)]
    
    # 3. Retrieve the IDs of the orders that belong to the winning cluster
    top_order_ids = [orders_data[i].id for i, label in enumerate(clustering.labels_) if label == top_cluster_id]

    # 4. Generate the Polygon with PostGIS
    # Retrieves both the convex hull geometry and its GeoJSON representation, as well as the centroid for display purposes
    result = db.query(
        func.ST_AsGeoJSON(func.ST_ConvexHull(func.ST_Collect(Order.position))).label("geometry"),
        func.ST_AsGeoJSON(func.ST_Centroid(func.ST_Collect(Order.position))).label("center")
    ).filter(Order.id.in_(top_order_ids)).first()

# 5. If we have a valid geometry, we save it in the history table with the order count for future analysis
    result = db.query(
        func.ST_ConvexHull(func.ST_Collect(Order.position)).label("geom_raw"),
        func.ST_AsGeoJSON(func.ST_ConvexHull(func.ST_Collect(Order.position))).label("geojson"),
        func.ST_AsGeoJSON(func.ST_Centroid(func.ST_Collect(Order.position))).label("center")
    ).filter(Order.id.in_(top_order_ids)).first()

    if result and result.geom_raw:
        # We save the raw geometry (not the GeoJSON) in the history table, along with the order count for this cluster
        save_hotspot_to_history(db, result.geom_raw, int(max(counts)))

    return {
        "active": True,
        "surge_multiplier": 1.5,
        "order_count": int(max(counts)),
        "geometry": json.loads(result.geojson),
        "center": json.loads(result.center)
    }

# Helper function to save the detected hotspot in the history table
def save_hotspot_to_history(db: Session, geom, count: int):
    """Enregistre la zone détectée dans l'historique."""
    if geom is None:
        return
    
    new_hotspot = Hotspot(
        geom=geom,
        order_count=count,
        surge_multiplier=1.5
    )
    db.add(new_hotspot)
    db.commit()

# --- Endpoint 5: Anomaly Detection for Drivers (V1) ---
@router.get("/drivers/anomalies")
def get_anomalies(db: Session = Depends(get_db)):
    """
    Detects only drivers outside the city's global boundary.
    """
    # We retrieve all drivers whose last position is NOT contained in any zone of category 'city_boundary'
    anomalies = db.query(Driver).filter(
        ~db.query(Zone).filter(
            Zone.category == 'city_boundary',
            func.ST_Contains(Zone.geom, Driver.last_position)
        ).exists()
    ).all()

    return [
        {
            "driver_id": d.id,
            "position": {
                "lat": db.scalar(func.ST_Y(d.last_position)),
                "lon": db.scalar(func.ST_X(d.last_position))
            },
            "status": "CRITICAL_OUT_OF_BOUNDS"
        } 
        for d in anomalies if d.last_position is not None
    ]

# --- Endpoint 6: Retrieve zones in GeoJSON format for the map ---
@router.get("/zones/geojson")
def get_zones_geojson(db: Session = Depends(get_db)):
    zones = db.query(Zone).all()
    features = []
    
    for z in zones:
        # We convert the geometry from the database to a Shapely geometry, then to GeoJSON format for Leaflet
        shapely_geom = to_shape(z.geom)
        
        features.append({
            "type": "Feature",
            "geometry": mapping(shapely_geom),
            "properties": {
                "id": z.id,
                "name": z.name,
                "category": z.category,  # keep the category for styling purposes on the frontend
                # A default color is added according to the category
                "color": "green" if z.category == "delivery" else "red"
            }
        })
        
    return {
        "type": "FeatureCollection", 
        "features": features
    }

# --- Endpoint 7: Retrieve the last known positions of drivers with anomaly status ---
@router.get("/drivers/positions")
def get_drivers_positions(db: Session = Depends(get_db)):
    # 1. Retrieve all driver IDs whose last position is NOT contained in any zone of category 'city_boundary'
    # This query returns a list of driver IDs that are outside the city boundary, which we will use to mark anomalies in the next step
    drivers_in_city_query = db.query(Driver.id).filter(
        db.query(Zone).filter(
            Zone.category == 'city_boundary',
            func.ST_Contains(Zone.geom, Driver.last_position)
        ).exists()
    ).all()
    
    # We create a set of "safe" driver IDs that are within the city boundary, which will allow us to easily check if a driver is an anomaly in the next step
    safe_driver_ids = {d[0] for d in drivers_in_city_query}

    # 2. Retrieve the last known positions of all drivers (we can limit to the most recent 1000 for performance reasons)
    drivers = db.query(Driver).order_by(Driver.id.desc()).limit(1000).all()
    
    positions = []
    for d in drivers:
        if d.last_position is not None:
            # If the ID is not on our "safe" list, it is an anomaly
            is_anomaly = d.id not in safe_driver_ids
            
            positions.append({
                "id": d.id,
                "lat": db.scalar(func.ST_Y(d.last_position)),
                "lon": db.scalar(func.ST_X(d.last_position)),
                "is_anomaly": is_anomaly
            })
            
    return positions