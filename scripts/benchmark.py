import requests
import random
import time

# Configuration
API_URL = "http://127.0.0.1:8000/can_accept_order"
NUM_TESTS = 2000  # Nombre de points à tester

# Limites géographiques approximatives de Nairobi pour le test
LAT_MIN, LAT_MAX = -1.45, -1.15
LON_MIN, LON_MAX = 36.65, 36.95

def run_benchmark():
    print(f"Starting the benchmark for {NUM_TESTS} requests...")
    
    start_time = time.time()
    success_count = 0
    authorized_count = 0

    for i in range(NUM_TESTS):
        # Génération d'un point aléatoire
        payload = {
            "driver_id": i,
            "lat": random.uniform(LAT_MIN, LAT_MAX),
            "lon": random.uniform(LON_MIN, LON_MAX)
        }
        
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                success_count += 1
                if response.json().get("authorized"):
                    authorized_count += 1
        except Exception as e:
            print(f"Request error {i}: {e}")

    total_time = time.time() - start_time
    
    print("-" * 30)
    print(f"Total time : {total_time:.2f} secondes")
    print(f"Average per request: {(total_time / NUM_TESTS) * 1000:.2f} ms")
    print(f"Successful requests: {success_count}/{NUM_TESTS}")
    print(f"Points in a zone: {authorized_count}")
    print("-" * 30)

if __name__ == "__main__":
    run_benchmark()