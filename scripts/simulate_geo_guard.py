import time
import random
import math
import sys
import os

# Configuration du chemin pour l'import de 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Driver
from geoalchemy2.elements import WKTElement

def simulate():
    db = SessionLocal()
    print(" Simulation Geo-Guard démarrée...")
    print(" Envoi des coordonnées GPS en temps réel...")

    # On récupère ou crée 15 drivers pour la démo
    drivers = db.query(Driver).limit(15).all()
    if not drivers:
        print("Création de nouveaux drivers pour la simulation...")
        for i in range(15):
            new_d = Driver(name=f"Livreur-{i+1}")
            db.add(new_d)
        db.commit()
        drivers = db.query(Driver).all()

    # Coordonnées centrales de Nairobi
    nairobi_lat, nairobi_lon = -1.286389, 36.817223
    
    # Angle pour chaque driver pour qu'ils partent dans des directions différentes
    angles = [random.uniform(0, 2 * math.pi) for _ in range(len(drivers))]
    distances = [random.uniform(0, 0.05) for _ in range(len(drivers))] # Distance du centre

    try:
        while True:
            for i, driver in enumerate(drivers):
                # Faire avancer le driver
                # 0.001 environ = 110 mètres
                speed = random.uniform(0.0005, 0.002) 
                
                # Certains drivers (ex: index 0 et 5) vont s'éloigner très loin pour sortir de la zone
                if i in [0, 5]:
                    speed = 0.005 

                distances[i] += speed
                
                # Calcul de la nouvelle position
                new_lat = nairobi_lat + (distances[i] * math.sin(angles[i]))
                new_lon = nairobi_lon + (distances[i] * math.cos(angles[i]))

                # Mise à jour dans PostGIS
                driver.last_position = WKTElement(f'POINT({new_lon} {new_lat})', srid=4326)
            
            db.commit()
            print(f"Update: {len(drivers)} positions mises à jour.", end='\r')
            time.sleep(2) # On simule un ping toutes les 2 secondes

    except KeyboardInterrupt:
        print(" Simulation arrêtée.")
    finally:
        db.close()

if __name__ == "__main__":
    simulate()