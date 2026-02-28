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


# Imports internes
from app.database import get_db
from app.models import Zone, Driver, Order
from app.schemas import DriverCheckRequest, DriverCheckResponse

router = APIRouter()

# Helper pour calculer la zone de chaleur actuelle
def get_current_surge_zone(db: Session):
    """Calcule la zone de chaleur actuelle à partir des commandes."""
    # Correction ici : on demande explicitement les valeurs X et Y
    orders_data = db.query(
        Order.id,
        func.ST_X(Order.position).label("lon"),
        func.ST_Y(Order.position).label("lat")
    ).all()

    if len(orders_data) < 5:
        return None
    
    # Transformation en tableau de flottants utilisable par Scikit-Learn
    coords = np.array([[float(o.lon), float(o.lat)] for o in orders_data])
    
    # DBSCAN peut maintenant travailler sur des chiffres
    clustering = DBSCAN(eps=0.002, min_samples=5).fit(coords)
    
    unique_labels, counts = np.unique(clustering.labels_[clustering.labels_ >= 0], return_counts=True)
    if len(unique_labels) == 0:
        return None
        
    top_cluster_id = unique_labels[np.argmax(counts)]
    top_order_ids = [orders_data[i].id for i, label in enumerate(clustering.labels_) if label == top_cluster_id]
    
    return db.query(func.ST_ConvexHull(func.ST_Collect(Order.position)))\
             .filter(Order.id.in_(top_order_ids)).scalar()

# --- Endpoint 1 : Vérification d'autorisation ---
@router.post("/can_accept_order", response_model=DriverCheckResponse)
def can_accept_order(request: DriverCheckRequest, db: Session = Depends(get_db)):
    # 1. Créer le point géographique du livreur
    point_wkt = f"POINT({request.lon} {request.lat})"
    point = ST_GeomFromText(point_wkt, 4326)

    # 2. Vérification Zone Autorisée (Zones Fixes)
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

    # 3. Vérification Bonus Dynamique (Heatmap)
    surge_active = False
    surge_zone_geom = get_current_surge_zone(db) # On appelle notre helper
    
    if surge_zone_geom:
        # On vérifie si le point du driver est DANS le polygone de chaleur
        is_in_surge = db.query(func.ST_Contains(surge_zone_geom, point)).scalar()
        surge_active = bool(is_in_surge)

    # 4. Mise à jour position Driver
    driver = db.query(Driver).filter(Driver.id == request.driver_id).first()
    if driver:
        driver.last_position = point
    else:
        new_driver = Driver(id=request.driver_id, last_position=point)
        db.add(new_driver)
    
    db.commit()

    # UN SEUL RETURN à la fin avec toutes les infos
    return DriverCheckResponse(
        authorized=authorized,
        surge_active=surge_active,
        multiplier=1.5 if surge_active else 1.0
    )

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


# --- Endpoint 3 : Zone de bonus dynamique (V1) ---
@router.get("/heatmap/top-cluster")
def get_dynamic_hotspot(db: Session = Depends(get_db)):
    """
    Identifie le cluster le plus dense et génère une zone dynamique (Polygone).
    """
    # 1. On récupère les données de clustering (on réutilise la logique précédente)
    orders_query = db.query(
        Order.id,
        Order.position,
        func.ST_X(Order.position).label("lon"),
        func.ST_Y(Order.position).label("lat")
    ).all()

    if not orders_query:
        return {"message": "Aucune commande disponible"}

    coords = np.array([[o.lon, o.lat] for o in orders_query])
    # eps=0.002 (env 200m), min_samples=5 pour trouver une vraie zone dense
    clustering = DBSCAN(eps=0.002, min_samples=5).fit(coords)
    labels = clustering.labels_

    # 2. Trouver l'ID du cluster le plus grand (excluant le bruit -1)
    unique_labels, counts = np.unique(labels[labels >= 0], return_counts=True)
    if len(unique_labels) == 0:
        return {"message": "Aucun hotspot détecté pour le moment"}
    
    top_cluster_id = unique_labels[np.argmax(counts)]

    # 3. Récupérer les IDs des commandes appartenant à ce top cluster
    top_order_ids = [orders_query[i].id for i, label in enumerate(labels) if label == top_cluster_id]

    # 4. Utiliser PostGIS pour créer le polygone "enveloppe" du cluster
    # On regroupe les points (ST_Collect) puis on dessine l'enveloppe (ST_ConvexHull)
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
        "suggested_multiplier": 1.5  # Exemple : Augmenter les tarifs de 50% ici
    }

# --- Endpoint 3 : Zone de bonus dynamique (V2) ---
@router.get("/heatmap/surge-zone")
def get_surge_zone(db: Session = Depends(get_db)):
    """
    Identifie le cluster le plus dense et génère une zone de bonus dynamique.
    """
  # 1. On demande explicitement les valeurs X et Y à la base de données
    orders_data = db.query(
        Order.id,
        func.ST_X(Order.position).label("lon"),
        func.ST_Y(Order.position).label("lat")
    ).all()

    if len(orders_data) < 5:
        return {"active": False, "message": "Pas assez de commandes pour un cluster"}

    # 2. On transforme les résultats en un tableau NumPy de FLOTTANTS
    # C'est ici que la correction se joue : on prend o.lon et o.lat (les valeurs)
    coords = np.array([[float(o.lon), float(o.lat)] for o in orders_data])

    # 3. Maintenant DBSCAN va fonctionner car il reçoit des chiffres
    clustering = DBSCAN(eps=0.002, min_samples=5).fit(coords)
    
    unique_labels, counts = np.unique(clustering.labels_[clustering.labels_ >= 0], return_counts=True)
    if len(unique_labels) == 0:
        return {"active": False, "message": "Aucun cluster dense détecté"}

    top_cluster_id = unique_labels[np.argmax(counts)]
    
    # On récupère les IDs des commandes qui font partie du cluster gagnant
    top_order_ids = [orders_data[i].id for i, label in enumerate(clustering.labels_) if label == top_cluster_id]

    # 4. Génération du Polygone avec PostGIS
    # ST_Collect regroupe les points, ST_ConvexHull crée l'enveloppe
    result = db.query(
        func.ST_AsGeoJSON(func.ST_ConvexHull(func.ST_Collect(Order.position))).label("geometry"),
        func.ST_AsGeoJSON(func.ST_Centroid(func.ST_Collect(Order.position))).label("center")
    ).filter(Order.id.in_(top_order_ids)).first()

# Récupération de la géométrie
    result = db.query(
        func.ST_ConvexHull(func.ST_Collect(Order.position)).label("geom_raw"),
        func.ST_AsGeoJSON(func.ST_ConvexHull(func.ST_Collect(Order.position))).label("geojson"),
        func.ST_AsGeoJSON(func.ST_Centroid(func.ST_Collect(Order.position))).label("center")
    ).filter(Order.id.in_(top_order_ids)).first()

    if result and result.geom_raw:
        # SAUVEGARDE DANS L'HISTORIQUE
        save_hotspot_to_history(db, result.geom_raw, int(max(counts)))

    return {
        "active": True,
        "surge_multiplier": 1.5,
        "order_count": int(max(counts)),
        "geometry": json.loads(result.geojson),
        "center": json.loads(result.center)
    }

# Helper pour sauvegarder la zone de chaleur dans l'historique
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

# --- Endpoint 4 : Anomalies de position des drivers ---
@router.get("/drivers/anomalies")
def get_anomalies(db: Session = Depends(get_db)):
    """
    Détecte uniquement les drivers hors de la frontière globale de la ville.
    """
    # On cherche les drivers qui ne sont contenus dans AUCUNE zone de type 'city_boundary'
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