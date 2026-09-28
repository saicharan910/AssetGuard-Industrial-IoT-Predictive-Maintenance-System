import os
import io
from fastapi.responses import StreamingResponse
import random
from datetime import datetime
import pandas as pd
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Database Setup: Supports both local SQLite and Cloud PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./telemetry.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TelemetryRecord(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    equipment_id = Column(String, index=True)
    temperature_celsius = Column(Float)
    vibration_mm_s = Column(Float)
    health_status = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

sensor_state = {"temp": 75.0, "vib": 2.0}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/telemetry")
def get_live_telemetry(db: Session = Depends(get_db)):
    global sensor_state
    
    sensor_state["temp"] += random.uniform(-1.5, 2.0)
    sensor_state["vib"] += random.uniform(-0.2, 0.3)
    sensor_state["temp"] = max(60.0, min(sensor_state["temp"], 110.0))
    sensor_state["vib"] = max(1.0, min(sensor_state["vib"], 6.0))

    temp = round(sensor_state["temp"], 2)
    vib = round(sensor_state["vib"], 2)
    status = "Warning: High Risk" if temp > 90.0 or vib > 4.5 else "Optimal"
    
    record = TelemetryRecord(
        equipment_id="MTR-001", 
        temperature_celsius=temp, 
        vibration_mm_s=vib, 
        health_status=status
    )
    
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@app.get("/api/history")
def get_history(limit: int = 30, db: Session = Depends(get_db)):
    return db.query(TelemetryRecord).order_by(TelemetryRecord.id.desc()).limit(limit).all()[::-1]

@app.get("/api/report")
def export_report():
    df = pd.read_sql("SELECT * FROM telemetry", con=engine)
    if df.empty:
        return {"message": "No data available."}

    # Convert DataFrame into an in-memory CSV text stream
    stream = io.StringIO()
    df.to_csv(stream, index=False)

    response = StreamingResponse(
        iter([stream.getvalue()]), 
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=assetguard_equipment_report.csv"
    return response


@app.get("/")
def root():
    return {"status": "online", "message": "AssetGuard IIoT API is running"}