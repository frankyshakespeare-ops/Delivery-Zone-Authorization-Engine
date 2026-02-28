import osmnx as ox
import sys
import os
import pandas as pd
from shapely.geometry import Polygon, MultiPolygon

# Configuration du chemin
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Zone
from geoalchemy2 import WKTElement

def import_nairobi_districts():
    print(" Récupération des quartiers de Nairobi depuis OpenStreetMap...")
    
    try:
        # On récupère les limites administratives
        districts = ox.features_from_place("Nairobi, Kenya", tags={"admin_level": "6"})

        db = SessionLocal()
        count = 0
        
        for _, row in districts.iterrows():
            # 1. GESTION DU NOM (Correction du bug nan)
            raw_name = row.get('name')
            
            # Si le nom est vide ou est un "NaN" de Pandas, on lui donne un nom par défaut ou on ignore
            if pd.isna(raw_name) or not str(raw_name).strip():
                district_name = f"Nairobi District {count + 1}"
            else:
                district_name = str(raw_name)

            # 2. GESTION DE LA GÉOMÉTRIE
            geometry = row.geometry
            if not isinstance(geometry, (Polygon, MultiPolygon)):
                continue

            # Conversion en WKT pour PostGIS
            wkt_element = WKTElement(geometry.wkt, srid=4326)
            
            new_zone = Zone(
                name=district_name, 
                category="delivery", 
                geom=wkt_element
            )
            db.add(new_zone)
            count += 1
        
        db.commit()
        print(f" {count} quartiers importés avec succès !")
        
    except Exception as e:
        print(f" Erreur lors de l'import : {e}")
        if 'db' in locals(): db.rollback()
    finally:
        if 'db' in locals(): db.close()

if __name__ == "__main__":
    import_nairobi_districts()