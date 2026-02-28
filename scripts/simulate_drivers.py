import random
import sys
import os
import requests
from app.database import SessionLocal
from app.models import Driver
from geoalchemy2 import WKTElement

# Configuration du chemin pour trouver le module 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. Définition des zones de Nairobi (Les "Sages")
min_lon, max_lon = 36.7, 36.9
min_lat, max_lat = -1.35, -1.20

db = SessionLocal()

try:
    # 2. Insertion massive de drivers à Nairobi
    total_sages = 100 
    drivers = []
    print(f"--- Phase 1 : Insertion de {total_sages} drivers à Nairobi ---")
    
    for i in range(total_sages):
        lon = random.uniform(min_lon, max_lon)
        lat = random.uniform(min_lat, max_lat)
        geom = WKTElement(f"POINT({lon} {lat})", srid=4326)
        # On ne met pas d'ID, la base de données gère l'auto-incrément
        drivers.append(Driver(last_position=geom)) 

    db.bulk_save_objects(drivers)
    db.commit()
    print(f" {total_sages} drivers insérés avec succès.")

    # 3. Ajout des "Rebelles" via l'API (Naivasha et Mombasa)
    rebelles = [
        {"id": 88888, "lat": -0.717, "lon": 36.435, "name": "Naivasha Rebel"},
        {"id": 99999, "lat": -4.043, "lon": 39.668, "name": "Mombasa Rebel"},
    ]

    print("\n--- Phase 2 : Test des anomalies via l'API ---")
    for r in rebelles:
        payload = {
            "driver_id": r["id"],
            "lat": r["lat"],
            "lon": r["lon"],
            "weather": "sunny"
        }
        try:
            # On appelle l'API pour que la logique de zone s'exécute
            response = requests.post("http://127.0.0.1:8000/can_accept_order", json=payload)
            if response.status_code == 200:
                status = response.json().get("authorized")
                print(f"Driver {r['id']} ({r['name']}) -> Autorisé: {status} (Attendu: False)")
            else:
                print(f" Erreur API pour {r['name']}: {response.status_code}")
        except Exception as e:
            print(f" Erreur de connexion : Ton serveur Uvicorn est-il lancé ?")

finally:
    db.close()