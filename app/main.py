
from fastapi import FastAPI
from app.routes import router as api_router
from fastapi.staticfiles import StaticFiles

# 1. On crée d'abord l'application
app = FastAPI(title="Delivery Zone API")

# 2. On inclut ensuite le router
app.include_router(api_router)

# 3. On monte ensuite les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Delivery Zone Authorization Engine"}