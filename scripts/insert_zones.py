import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Zone
from geoalchemy2 import WKTElement
from shapely import wkt

# Définition de quelques zones approximatives à Nairobi
zones_data = [
    {
        "name": "CBD",
        "wkt_polygon": "POLYGON((36.821 -1.292, 36.830 -1.292, 36.830 -1.285, 36.821 -1.285, 36.821 -1.292))"
    },
    {
        "name": "Westlands",
        "wkt_polygon": "POLYGON((36.810 -1.265, 36.825 -1.265, 36.825 -1.275, 36.810 -1.275, 36.810 -1.265))"
    },
    {
        "name": "Karen",
        "wkt_polygon": "POLYGON((36.700 -1.320, 36.720 -1.320, 36.720 -1.340, 36.700 -1.340, 36.700 -1.320))"
    },
    {
        "name": "Kilimani",
        "wkt_polygon": "POLYGON((36.785 -1.285, 36.805 -1.285, 36.805 -1.305, 36.785 -1.305, 36.785 -1.285))"
    },
    {
        "name": "Industrial Area",
        "wkt_polygon": "POLYGON((36.835 -1.300, 36.860 -1.300, 36.860 -1.330, 36.835 -1.330, 36.835 -1.300))"
    }
]


db = SessionLocal()
try:
    for z in zones_data:
        # On vérifie si la zone existe déjà pour éviter les doublons
        existing = db.query(Zone).filter(Zone.name == z["name"]).first()
        if not existing:
            geom = WKTElement(z["wkt_polygon"], srid=4326)
            zone = Zone(name=z["name"], geom=geom)
            db.add(zone)
            print(f"Insertion de la zone : {z['name']}")
    db.commit()
    print("--- Toutes les zones ont été traitées avec succès. ---")
except Exception as e:
    db.rollback()
    print(f"Erreur lors de l'insertion : {e}")
finally:
    db.close()