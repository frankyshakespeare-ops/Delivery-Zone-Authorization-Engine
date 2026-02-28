
from fastapi import FastAPI
from app.routes import router as api_router
from fastapi.staticfiles import StaticFiles

# 1. create the application first
app = FastAPI(title="Delivery Zone API")

# 2. include the API router
app.include_router(api_router)

# 3. mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Delivery Zone Authorization Engine"}