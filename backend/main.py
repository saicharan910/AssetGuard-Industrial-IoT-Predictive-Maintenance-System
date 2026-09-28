import os
import io
import json
import random
import asyncio
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# 1. Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./telemetry.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
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
    allow_headers=["*"],
)

# 2. Multi-Asset Profiles & ML Baseline
ASSETS = {
    "MTR-001": {"temp": 75.0, "vib": 2.0},
    "PUMP-101": {"temp": 60.0, "vib": 1.5},
    "FAN-042": {"temp": 45.0, "vib": 1.0}
}

# Baseline normal operational dataset to fit Isolation Forest
X_baseline = np.array([
    [75.0, 2.0], [74.5, 2.1], [76.0, 1.9], [73.8, 2.2],
    [60.0, 1.5], [59.5, 1.6], [61.0, 1.4], [58.9, 1.5],
    [45.0, 1.0], [44.8, 1.1], [46.2, 0.9], [43.9, 1.2]
])
ml_model = IsolationForest(contamination=0.08, random_state=42)
ml_model.fit(X_baseline)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"status": "online", "message": "AssetGuard IIoT ML Engine is running"}

# 3. WebSocket Real-Time Stream with Machine Learning
@app.websocket("/ws/telemetry/{equipment_id}")
async def websocket_telemetry(websocket: WebSocket, equipment_id: str, db: Session = Depends(get_db)):
    await websocket.accept()
    if equipment_id not in ASSETS:
        equipment_id = "MTR-001"
    
    try:
        while True:
            state = ASSETS[equipment_id]
            state["temp"] += random.uniform(-1.8, 2.2)
            state["vib"] += random.uniform(-0.25, 0.35)
            
            temp = round(max(20.0, min(state["temp"], 115.0)), 2)
            vib = round(max(0.5, min(state["vib"], 7.0)), 2)
            
            # Machine Learning Inference: -1 indicates anomaly, 1 indicates normal
            prediction = ml_model.predict([[temp, vib]])[0]
            status = "Warning: High Risk (ML Detected)" if prediction == -1 else "Optimal"
            
            record = TelemetryRecord(
                equipment_id=equipment_id,
                temperature_celsius=temp,
                vibration_mm_s=vib,
                health_status=status
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            
            await websocket.send_json({
                "id": record.id,
                "timestamp": record.timestamp.isoformat(),
                "equipment_id": equipment_id,
                "temperature_celsius": temp,
                "vibration_mm_s": vib,
                "health_status": status
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

@app.get("/api/history/{equipment_id}")
def get_history(equipment_id: str, limit: int = 30, db: Session = Depends(get_db)):
    return db.query(TelemetryRecord).filter(
        TelemetryRecord.equipment_id == equipment_id
    ).order_by(TelemetryRecord.id.desc()).limit(limit).all()[::-1]

# 4. Direct CSV File Download Endpoint
@app.get("/api/report")
def export_report():
    df = pd.read_sql("SELECT * FROM telemetry", con=engine)
    if df.empty:
        return {"message": "No data available."}

    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=assetguard_ml_report.csv"
    return response