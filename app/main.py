from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="Delivery Zone Authorization Engine",
    description="API pour vérifier si un livreur peut accepter une commande en fonction de sa position.",
    version="1.0"
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Bienvenue sur l'API de zones de livraison"}