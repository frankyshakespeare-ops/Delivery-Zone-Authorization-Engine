from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# À adapter si tu utilises Docker ou des identifiants différents
# On ajoute :5433 après localhost
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