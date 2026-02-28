''' from fastapi import FastAPI
from app.routes import router

from app.routes import router as api_router
app.include_router(api_router)

app = FastAPI(
    title="Delivery Zone Authorization Engine",
    description="API to check if a delivery person can accept an order based on their location.",
    version="1.0"
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Welcome to the Delivery Zone Authorization Engine API!"}
'''
from fastapi import FastAPI
from app.routes import router as api_router

# 1. On crée d'abord l'application
app = FastAPI(title="Delivery Zone API")

# 2. On inclut ensuite le router
app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Delivery Zone Authorization Engine"}