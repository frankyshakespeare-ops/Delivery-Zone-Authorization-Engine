from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

#To adapt if you use Docker or different credentials
# I add :5433 after localhost because we are using a custom port for PostgreSQL in Docker. Adjust as needed for your setup.
DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/delivery_zones"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()