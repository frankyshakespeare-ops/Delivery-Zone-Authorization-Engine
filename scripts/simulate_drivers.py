import random
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Driver
from geoalchemy2 import WKTElement

# Définir une bounding box approximative de Nairobi
min_lon, max_lon = 36.7, 36.9
min_lat, max_lat = -1.35, -1.20

db = SessionLocal()
batch_size = 1000
total = 100000

for i in range(0, total, batch_size):
    drivers = []
    for j in range(batch_size):
        lon = random.uniform(min_lon, max_lon)
        lat = random.uniform(min_lat, max_lat)
        point_wkt = f"POINT({lon} {lat})"
        geom = WKTElement(point_wkt, srid=4326)
        drivers.append(Driver(id=i+j+1, last_position=geom))  # Attention : les IDs doivent être uniques
    db.bulk_save_objects(drivers)
    db.commit()
    print(f"Inséré {i+batch_size} drivers")

db.close()