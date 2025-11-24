"""Data models and database schema"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from config import settings

Base = declarative_base()

class SensorReading(Base):
    __tablename__ = "sensor_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    device_id = Column(String, index=True)
    ro = Column(Float)
    rs = Column(Float)
    ratio = Column(Float, index=True)
    vout = Column(Float)
    status = Column(String)
    is_alert = Column(Boolean, default=False, index=True)

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True)
    name = Column(String)
    url = Column(String)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime)
    calibration_ro = Column(Float)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    device_id = Column(String, index=True)
    alert_type = Column(String)  # 'spoiled', 'warning'
    ratio_value = Column(Float)
    phone_number = Column(String)
    call_sid = Column(String)
    is_resolved = Column(Boolean, default=False)

# Pydantic models for API
class SensorReadingCreate(BaseModel):
    device_id: str
    ro: float
    rs: float
    ratio: Optional[float] = None
    vout: float
    status: str = ""

class SensorReadingResponse(BaseModel):
    id: int
    timestamp: datetime
    device_id: str
    ro: float
    rs: float
    ratio: float
    vout: float
    status: str
    is_alert: bool
    
    class Config:
        from_attributes = True

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()