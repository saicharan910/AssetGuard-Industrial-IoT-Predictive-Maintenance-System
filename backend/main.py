from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import random
from datetime import datetime
import pandas as pd

# 1. Database Setup
engine = create_engine("sqlite:///./telemetry.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Database Model
class TelemetryRecord(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    equipment_id = Column(String, index=True)
    temperature_celsius = Column(Float)
    vibration_mm_s = Column(Float)
    health_status = Column(String)

Base.metadata.create_all(bind=engine)

# 3. FastAPI App Setup
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sensor_state = {"temp": 75.0, "vib": 2.0}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. API Endpoints
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
def trigger_report():
    df = pd.read_sql("SELECT * FROM telemetry", con=engine)
    if df.empty:
        return {"message": "No data available."}
    
    total_warnings = len(df[df['health_status'] == "Warning: High Risk"])
    df.to_csv("equipment_report.csv", index=False)
    
    return {
        "status": "Report generated", 
        "total_anomalies_detected": total_warnings
    }