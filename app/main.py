
from fastapi import FastAPI
from app.routes import router as api_router

# 1. On crée d'abord l'application
app = FastAPI(title="Delivery Zone API")

# 2. On inclut ensuite le router
app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Delivery Zone Authorization Engine"}