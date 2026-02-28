import sys
import os

# Ajout du chemin racine pour que Python trouve le module 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
# IMPORTANT : On importe tous les modèles pour que Base les connaisse
from app.models import Zone, Driver, Order 

def reset_database():
    print(" Connexion à la base de données...")
    
    # 1. On supprime tout pour repartir de zéro
    print("  Suppression des anciennes tables (drop_all)...")
    Base.metadata.drop_all(bind=engine)
    
    # 2. On recrée tout avec la nouvelle structure (y compris lat/lon dans Order)
    print("  Création des nouvelles tables (create_all)...")
    Base.metadata.create_all(bind=engine)
    
    print(" Base de données mise à jour avec succès !")

if __name__ == "__main__":
    try:
        reset_database()
    except Exception as e:
        print(f" Erreur lors de la mise à jour : {e}")