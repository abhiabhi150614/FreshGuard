"""Sensor data collection and processing service"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import requests
import redis
import structlog
from sqlalchemy.orm import Session
from models import SensorReading, Device, get_db, SessionLocal
from config import settings

logger = structlog.get_logger()

class SensorService:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.session = SessionLocal()
    
    def fetch_device_status(self, device_url: str, timeout: float = None) -> Dict[str, Any]:
        """Fetch status from ESP32 device with error handling"""
        timeout = timeout or settings.REQUEST_TIMEOUT
        url = device_url.rstrip("/") + "/status"
        
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("Device timeout", device_url=device_url)
            raise
        except requests.exceptions.ConnectionError:
            logger.error("Device connection failed", device_url=device_url)
            raise
        except Exception as e:
            logger.error("Device fetch failed", device_url=device_url, error=str(e))
            raise
    
    def normalize_reading(self, raw_data: Dict[str, Any], device_id: str) -> Dict[str, Any]:
        """Normalize and validate sensor reading"""
        def safe_float(value, default=0.0):
            try:
                return float(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        ro = safe_float(raw_data.get("Ro", 0.0))
        rs = safe_float(raw_data.get("Rs", 0.0))
        ratio = safe_float(raw_data.get("ratio"))
        
        if ratio == 0.0 and ro > 0:
            ratio = rs / ro
        
        return {
            "device_id": device_id,
            "ro": ro,
            "rs": rs,
            "ratio": ratio,
            "vout": safe_float(raw_data.get("Vout", 0.0)),
            "status": raw_data.get("status", ""),
            "timestamp": datetime.utcnow()
        }
    
    def save_reading(self, reading_data: Dict[str, Any]) -> SensorReading:
        """Save sensor reading to database"""
        is_alert = reading_data["ratio"] <= settings.RATIO_WARNING
        
        reading = SensorReading(
            device_id=reading_data["device_id"],
            ro=reading_data["ro"],
            rs=reading_data["rs"],
            ratio=reading_data["ratio"],
            vout=reading_data["vout"],
            status=reading_data["status"],
            is_alert=is_alert,
            timestamp=reading_data["timestamp"]
        )
        
        self.session.add(reading)
        self.session.commit()
        self.session.refresh(reading)
        
        cache_key = f"latest_reading:{reading_data['device_id']}"
        self.redis_client.setex(
            cache_key, 
            300,
            json.dumps(reading_data, default=str)
        )
        
        logger.info("Reading saved", 
                   device_id=reading_data["device_id"],
                   ratio=reading_data["ratio"],
                   is_alert=is_alert)
        
        return reading
    
    def get_latest_reading(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get latest reading from cache or database"""
        cache_key = f"latest_reading:{device_id}"
        cached = self.redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        reading = self.session.query(SensorReading)\
            .filter(SensorReading.device_id == device_id)\
            .order_by(SensorReading.timestamp.desc())\
            .first()
        
        if reading:
            return {
                "device_id": reading.device_id,
                "ro": reading.ro,
                "rs": reading.rs,
                "ratio": reading.ratio,
                "vout": reading.vout,
                "status": reading.status,
                "timestamp": reading.timestamp,
                "is_alert": reading.is_alert
            }
        
        return None
    
    def get_readings_history(self, device_id: str, hours: int = 24, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get historical readings for a device"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        readings = self.session.query(SensorReading)\
            .filter(
                SensorReading.device_id == device_id,
                SensorReading.timestamp >= since
            )\
            .order_by(SensorReading.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [{
            "timestamp": r.timestamp,
            "device_id": r.device_id,
            "ro": r.ro,
            "rs": r.rs,
            "ratio": r.ratio,
            "vout": r.vout,
            "status": r.status,
            "is_alert": r.is_alert
        } for r in readings]
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()