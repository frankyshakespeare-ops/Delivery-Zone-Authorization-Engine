import sys
import os
import random
from app.database import SessionLocal
from app.models import Order
from geoalchemy2.elements import WKTElement

# On ajoute le dossier parent au chemin de recherche de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
# ... le reste de tes imports

db = SessionLocal()

def create_cluster(base_lat, base_lon, count, spread=0.005):
    """Génère un groupe de commandes autour d'un point central"""
    for _ in range(count):
        lat = base_lat + random.uniform(-spread, spread)
        lon = base_lon + random.uniform(-spread, spread)
        point = f"POINT({lon} {lat})"
        order = Order(
            lat=lat, 
            lon=lon, 
            position=WKTElement(point, srid=4326)
        )
        db.add(order)

# 1. Cluster dense dans le CBD (15 commandes)
create_cluster(-1.283, 36.823, 15)

# 2. Cluster dans Westlands (10 commandes)
create_cluster(-1.265, 36.808, 10)

# 3. Points isolés (Bruit pour DBSCAN)
create_cluster(-1.310, 36.750, 3, spread=0.02)

try:
    db.commit()
    print(" 28 commandes de test insérées avec succès !")
except Exception as e:
    db.rollback()
    print(f" Erreur : {e}")
finally:
    db.close()