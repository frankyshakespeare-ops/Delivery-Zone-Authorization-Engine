from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="Delivery Zone Authorization Engine",
    description="API to check if a delivery person can accept an order based on their location.",
    version="1.0"
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Welcome to the Delivery Zone Authorization Engine API!"}